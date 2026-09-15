#!/usr/bin/env python3
"""R465 本地门判**延迟分解**探针 (真机 / 真权重 / 产品实发 prompt)。

问题 (R464 现场): 门开臂被门控轮墙钟 40.7/40.9/70.8/102.2 s vs 门关臂 0.04–0.08 s
⇒ 38.5% token 降幅换来 +40~100 s 延迟。目标 ≤10 s/门控轮。

本探针只做**分解**, 不改产品: 把「服务启停(model load)」/「prompt 评估 (eval)」/「生成 (gen)」
三段分别计时, 并对两个候选杠杆各做**单变量**臂:
  A1 = -t 1, cache_prompt=false   ← 现役产品口径 (LlamaCppGeneratorOptions.Threads 默认 1 + ReuseFor(false))
  A2 = -t 2, cache_prompt=false   ← 杠杆① 线程数 (本机 nproc=2)
  A3 = -t 2, cache_prompt=true    ← 杠杆② 前缀缓存 (R429 曾实测: 部分前缀复用会改 token 序列 ⇒ 判据须逐条比对)

口径纪律:
  * prompt = 产品落盘 dump 的 verbatim 门判 prompt, 再经 /apply-template (+add_generation_prompt)
    —— 与产品 LlamaCppProvider.RenderAsync 同链路;
  * 请求体字段与 LlamaCppJson/CompletionProfiles 逐字段同构 (greedy, seed 0, return_tokens);
  * token 真值只取 tokens_evaluated / timings.prompt_n / timings.cache_n (禁字符估算, R443 铁律);
  * 判据面 = 1:1 移植产品 TurnGateJudge.Parse (R462-W 已逐条对齐 13/13 产品自带用例)。
"""
import argparse, hashlib, json, os, re, subprocess, sys, time, urllib.request

BIN_DEFAULT = "/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server"
CORPUS_DEFAULT = "/home/agentuser/AgentFramework/eval/rover/r462/corpus-r462-w.json"
MODEL_DEFAULT = "/home/agentuser/.agentframework/models/qwen2.5-3b-instruct-q4km.gguf"

THINK_OPEN, THINK_CLOSE = "<think>", "</think>"
_KW_SKIP = ("无新增", "无新", "无需", "跳过", "认可", "采纳")
_KW_PASS = ("有新增", "新要求", "新问题", "纠正", "继续", "需要")
_LETTER = re.compile(r"(?<![A-Za-z])([SsPp])(?![A-Za-z])")


def gate_parse(raw):
    """1:1 移植 TurnGateJudge.Parse (src/agent.modelqueue/LocalGenerationPort.cs:251-379)。"""
    if raw is None or not raw.strip():
        return None, "empty"
    text = raw.strip()
    close = text.rfind(THINK_CLOSE)
    if close >= 0:
        conclusion = text[close + len(THINK_CLOSE):]
    else:
        if text.rfind(THINK_OPEN) >= 0:
            return None, "thinking_truncated"
        u = text.encode("utf-16-le")
        conclusion = u[-128:].decode("utf-16-le", "ignore") if len(u) > 128 else text
    conclusion = conclusion.strip()
    if not conclusion:
        return None, "empty_conclusion"
    last_skip = last_pass = -1
    for m in _LETTER.finditer(conclusion):
        if m.group(1) in "Ss":
            last_skip = max(last_skip, m.start())
        else:
            last_pass = max(last_pass, m.start())
    for pat in _KW_SKIP + _KW_PASS:
        k = conclusion.rfind(pat)
        if k < 0:
            continue
        if pat in _KW_SKIP:
            last_skip = max(last_skip, k)
        else:
            last_pass = max(last_pass, k)
    if last_skip < 0 and last_pass < 0:
        return None, "no_marker"
    return ("S" if last_skip > last_pass else "P"), "ok"


def build_args(binp, model, port, ctx, threads):
    """与产品 LlamaServerHost.BuildArgumentList 逐字段同构 (embedding=false)。"""
    a = [binp, "-m", model, "--host", "127.0.0.1", "--port", str(port), "-c", str(ctx)]
    if threads > 0:
        a += ["-t", str(threads)]
    a += ["-np", "1", "--cache-type-k", "f32", "--cache-type-v", "f32", "--flash-attn", "off", "--jinja"]
    return a


def rss_mb(pid):
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith("VmRSS"):
                return int(line.split()[1]) // 1024
    except Exception:
        pass
    return -1


def wait_health(port, timeout=600, pid=None):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pid is not None and not os.path.exists(f"/proc/{pid}"):
            return None
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as r:
                if r.status == 200:
                    return time.time() - t0
        except Exception:
            time.sleep(0.5)
    return None


def post(port, path, body, timeout=900):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/{path}",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    return d, round(time.time() - t0, 3)


def render(port, text):
    d, w = post(port, "apply-template", {"messages": [{"role": "user", "content": text}],
                                         "add_generation_prompt": True})
    return d.get("prompt") or "", w


def complete(port, prompt, n_predict, cache_prompt):
    body = {"prompt": prompt, "n_predict": n_predict, "samplers": ["temperature"], "temperature": 0,
            "top_k": 0, "top_p": 1, "min_p": 0, "repeat_penalty": 1, "seed": 0,
            "cache_prompt": bool(cache_prompt), "return_tokens": True, "stream": False, "n_probs": 0}
    d, w = post(port, "completion", body)
    tm = d.get("timings") or {}
    return {
        "wall_s": w,
        "eval_total": d.get("tokens_evaluated"),
        "prompt_n": tm.get("prompt_n"),
        "cache_n": tm.get("cache_n"),
        "predicted_n": d.get("tokens_predicted", tm.get("predicted_n")),
        "gen_ms": tm.get("predicted_ms"),
        "prompt_ms": tm.get("prompt_ms"),
        "content": d.get("content") or "",
    }


def run_arm(tag, binp, model, corpus, port, ctx, threads, cache_prompt, out_dir, repeat_first=True):
    log = os.path.join(out_dir, f"srv-{tag}.log")
    args = build_args(binp, model, port, ctx, threads)
    t_start = time.time()
    with open(log, "wb") as f:
        p = subprocess.Popen(args, stdout=f, stderr=subprocess.STDOUT, cwd="/tmp")
    try:
        load_s = wait_health(port, 600, p.pid)
        if load_s is None:
            print(f"[{tag}] SERVER_NOT_READY log={log}", flush=True)
            return None
        rows = []
        for i, c in enumerate(corpus, 1):
            want = "S" if c["want"] == "skip" else "P"
            rp, render_s = render(port, c["prompt"])
            r = complete(port, rp, 512, cache_prompt)
            v, why = gate_parse(r["content"])
            rows.append({"i": i, "src": c["src"], "turn": c["turn"], "family": c["family"],
                         "want": want, "got": v or "?", "reason": why,
                         "render_sha16": hashlib.sha256(rp.encode()).hexdigest()[:16].upper(),
                         "render_len": len(rp), "render_s": render_s, **{k: r[k] for k in
                         ("wall_s", "eval_total", "prompt_n", "cache_n", "predicted_n", "gen_ms", "prompt_ms")},
                         "raw_head": r["content"].strip().replace("\n", "\\n")[:90]})
            print(f"  [{tag}] {i}/{len(corpus)} want={want} got={rows[-1]['got']} "
                  f"wall={r['wall_s']}s eval={r['eval_total']} prompt_n={r['prompt_n']} cache_n={r['cache_n']} "
                  f"gen={r['predicted_n']} rss={rss_mb(p.pid)}MB", flush=True)
        rep = None
        if repeat_first:
            r = complete(port, corpus[0]["prompt"], 512, cache_prompt)
            rep = {"wall_s": r["wall_s"], "eval_total": r["eval_total"], "prompt_n": r["prompt_n"],
                   "cache_n": r["cache_n"]}
            print(f"  [{tag}] repeat#1 → {rep}", flush=True)
        res = {"tag": tag, "threads": threads, "cache_prompt": cache_prompt, "ctx": ctx,
               "load_s": round(load_s, 2), "load_total_s": round(time.time() - t_start, 2),
               "rss_mb": rss_mb(p.pid), "args": args[1:], "repeat_first": rep, "rows": rows,
               "verdicts": "".join(r["got"] for r in rows),
               "walls": [r["wall_s"] for r in rows]}
        json.dump(res, open(os.path.join(out_dir, f"arm-{tag}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        return res
    finally:
        p.terminate()
        try:
            p.wait(timeout=20)
        except Exception:
            p.kill()


def pick(corpus, n):
    """分层取子集: 正类(ack, want=skip) 与负类(真实诉求, want=pass) 各半, 保持产品顺序。"""
    pos = [c for c in corpus if c["want"] == "skip"]
    neg = [c for c in corpus if c["want"] != "skip"]
    half = n // 2
    sel = pos[:half] + neg[:n - half]
    order = {id(c): i for i, c in enumerate(corpus)}
    return sorted(sel, key=lambda c: order[id(c)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--bin", default=BIN_DEFAULT)
    ap.add_argument("--corpus", default=CORPUS_DEFAULT)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--ctx", type=int, default=4608)
    ap.add_argument("--base-port", type=int, default=48810)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    corpus = json.load(open(a.corpus, encoding="utf-8"))
    sub = pick(corpus, a.n)
    json.dump(sub, open(os.path.join(a.out_dir, "corpus-subset.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"[setup] corpus n={len(corpus)} subset n={len(sub)} ctx={a.ctx} model={a.model}", flush=True)
    arms = [("A1_t1_cacheF", 1, False), ("A2_t2_cacheF", 2, False), ("A3_t2_cacheT", 2, True)]
    out = {}
    for k, (tag, th, cp) in enumerate(arms):
        r = run_arm(tag, a.bin, a.model, sub, a.base_port + k, a.ctx, th, cp, a.out_dir)
        if r is None:
            print(f"[{tag}] 失败", flush=True)
            continue
        base = out.get("A1_t1_cacheF")
        same = None if base is None else (r["verdicts"] == base["verdicts"])
        print(f"[{tag}] load={r['load_s']}s walls={r['walls']} verdicts={r['verdicts']} "
              f"vs_A1_same={same} rss={r['rss_mb']}MB", flush=True)
        out[tag] = r
    json.dump({k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in out.items()},
              open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[done] summary → " + os.path.join(a.out_dir, "summary.json"), flush=True)


if __name__ == "__main__":
    sys.exit(main())
