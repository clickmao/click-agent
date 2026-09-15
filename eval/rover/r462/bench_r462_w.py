#!/usr/bin/env python3
"""R462 W-臂 (权重/量化档位能力探针) —— 只吃**产品实发**门判 prompt, 不重建。

语料: /tmp/r462_corpus.json (由产品落盘 dump-*.jsonl 抽 verbatim prompt)
  * 14 条 负类 = RJ-REAL 真实驱动消息(「继续下一轮」×13 + 全候选推进令×1) ⇒ oracle: 禁跳(P)
  * 14 条 正类 = RC-M20 Ack 族(「谢谢，收到。」等 t7–t13 ×2 轮)      ⇒ oracle: 可跳(S)
  oracle 来源 = grid/task-M20.json expected[] + grid/meta.json rule_label (机械, 与 r1 无关)

口径: llama.cpp /completion, samplers=["temperature"], temp=0 (greedy), cache_prompt=false
      —— 与产品 LlamaCppClient 完全同参; token 真值取 tokens_evaluated/predicted_n (R443 铁律)

用法: python3 r462_w_bench.py --model <gguf> --tag <tag> --port 48790 --ctx 1024 --out <json>
"""
import hashlib, argparse, json, os, re, subprocess, sys, time, urllib.request, urllib.error

BIN = "/tmp/llama-full/build/bin/llama-server"
CORPUS = "/tmp/r462_corpus.json"


def start_server(model, port, ctx, log):
    args = [BIN, "-m", model, "--host", "127.0.0.1", "--port", str(port), "-c", str(ctx),
            "-t", "2", "-np", "1", "--cache-type-k", "f32", "--cache-type-v", "f32",
            "--flash-attn", "off", "--jinja", "-b", "512", "-ub", "512"]
    f = open(log, "wb")
    p = subprocess.Popen(args, stdout=f, stderr=subprocess.STDOUT, cwd="/tmp")
    return p, args


def wait_health(port, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(2)
    return False


def apply_template(port, text):
    """产品同源 (LlamaCppProvider.RenderAsync ⇒ POST /apply-template, add_generation_prompt=true)。"""
    body = json.dumps({"messages": [{"role": "user", "content": text}],
                       "add_generation_prompt": True}).encode("utf-8")
    req = urllib.request.Request(f"http://127.0.0.1:{port}/apply-template", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    return d.get("prompt") or ""


def complete(port, prompt, n_predict=512):
    # 请求体 = 产品 CompletionRequest 全字段 (LlamaCppJson.cs:7-22 + CompletionProfiles.cs:11-18)
    body = json.dumps({"prompt": prompt, "n_predict": n_predict, "samplers": ["temperature"],
                       "temperature": 0, "top_k": 0, "top_p": 1, "min_p": 0, "repeat_penalty": 1,
                       "seed": 0, "cache_prompt": False, "return_tokens": True,
                       "stream": False, "n_probs": 0}).encode("utf-8")
    req = urllib.request.Request(f"http://127.0.0.1:{port}/completion", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    d["_wall_s"] = round(time.time() - t0, 2)
    return d


THINK_CLOSE = "</think>"
THINK_OPEN = "<think>"
_KW_SKIP = ("无新增", "无新", "无需", "跳过", "认可", "采纳")
_KW_PASS = ("有新增", "新要求", "新问题", "纠正", "继续", "需要")
_LETTER = re.compile(r"(?<![A-Za-z])([SsPp])(?![A-Za-z])")


def gate_parse(raw):
    """1:1 移植产品 TurnGateJudge.Parse (src/agent.modelqueue/LocalGenerationPort.cs:336-379)。

    返回 (verdict, reason): verdict ∈ {"S","P",None}; None = 未判定 (产品侧降级远端 = Pass)。
    reason ∈ empty / thinking_truncated / empty_conclusion / no_marker / ok。
    """
    if raw is None or not raw.strip():
        return None, "empty"
    text = raw.strip()

    close = text.rfind(THINK_CLOSE)
    if close >= 0:
        conclusion = text[close + len(THINK_CLOSE):]
    else:
        if text.rfind(THINK_OPEN) >= 0:
            return None, "thinking_truncated"          # 有开无闭 = 被 max_tokens 截断
        u = text.encode("utf-16-le")                   # .NET 按 UTF-16 码元取窗
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--port", type=int, default=48790)
    ap.add_argument("--ctx", type=int, default=1024)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    corpus = json.load(open(CORPUS, encoding="utf-8"))
    log = f"/tmp/r462_srv_{a.tag}.log"
    p, args = start_server(a.model, a.port, a.ctx, log)
    print(f"[{a.tag}] pid={p.pid} args={' '.join(args[1:])}")
    try:
        if not wait_health(a.port):
            print(f"[{a.tag}] SERVER_NOT_READY (log={log})")
            return 3
        rows, t0 = [], time.time()
        for i, c in enumerate(corpus, 1):
            want_skip = (c["want"] == "skip")
            try:
                rp = apply_template(a.port, c["prompt"])
                rsha = hashlib.sha256(rp.encode("utf-8")).hexdigest()[:16].upper()
                d = complete(a.port, rp)
                txt = d.get("content") or ""
                v, why = gate_parse(txt)
                v = v or "?"
                rows.append({"i": i, "src": c["src"], "turn": c["turn"], "family": c["family"],
                             "want": "S" if want_skip else "P", "got": v,
                             "ok": (v == ("S" if want_skip else "P")),
                             "render_len": len(rp), "render_sha16": rsha,
                             "prompt_truth": (d.get("tokens_evaluated") if d.get("tokens_evaluated") is not None else (d.get("timings") or {}).get("prompt_n")),
                             "gen_truth": (d.get("tokens_predicted") if d.get("tokens_predicted") is not None else ((d.get("predicted_n") if d.get("predicted_n") is not None else (d.get("timings") or {}).get("predicted_n")))),
                             "wall_s": d["_wall_s"], "reason": why,
                             "raw": txt[:4000], "raw_head": txt.strip().replace("\n", "\\n")[:120]})
            except Exception as e:
                rows.append({"i": i, "src": c["src"], "want": "S" if want_skip else "P", "got": "ERR",
                             "ok": False, "err": f"{type(e).__name__}: {e}"[:200]})
            print(f"  {i}/{len(corpus)} want={'S' if want_skip else 'P'} got={rows[-1]['got']} "
                  f"gen={rows[-1].get('gen_truth')} {rows[-1].get('wall_s')}s", flush=True)

        neg = [r for r in rows if r["want"] == "P"]
        pos = [r for r in rows if r["want"] == "S"]
        res = {"tag": a.tag, "model": a.model, "ctx": a.ctx, "n": len(rows),
               "acc": round(sum(r["ok"] for r in rows) / len(rows), 4),
               "false_skip_n": sum(1 for r in neg if r["got"] == "S"),
               "false_skip_rate": round(sum(1 for r in neg if r["got"] == "S") / len(neg), 4),
               "miss_skip_n": sum(1 for r in pos if r["got"] == "P"),
               "unparsed_n": sum(1 for r in rows if r["got"] in ("?", "ERR")),
               "undecided_n": sum(1 for r in rows if r.get("reason") not in (None, "ok")),
               "skip_n": sum(1 for r in rows if r["got"] == "S"),
               "skip_precision": round(sum(1 for r in rows if r["got"] == "S" and r["want"] == "S")
                                       / max(1, sum(1 for r in rows if r["got"] == "S")), 4),
               "skip_recall": round(sum(1 for r in rows if r["got"] == "S" and r["want"] == "S")
                                    / max(1, sum(1 for r in rows if r["want"] == "S")), 4),
               "gen_truth_sum": sum(r.get("gen_truth") or 0 for r in rows),
               "elapsed_s": round(time.time() - t0, 1), "rows": rows}
        json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[{a.tag}] acc={res['acc']} 假跳={res['false_skip_n']}/{len(neg)} 漏跳={res['miss_skip_n']}/{len(pos)} "
              f"未判定={res['undecided_n']} S精度={res['skip_precision']} S召回={res['skip_recall']} "
              f"gen={res['gen_truth_sum']} {res['elapsed_s']}s → {a.out}")
        return 0
    finally:
        p.terminate()
        try:
            p.wait(timeout=20)
        except Exception:
            p.kill()


if __name__ == "__main__":
    sys.exit(main())
