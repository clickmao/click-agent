#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R448 真机探针：判官 prompt 侧「限长思考」消融（保留思考，只压缩长度）。

预注册见 eval/rover/r448/prereg.json（先落盘；sha256/mtime 写进结果）。
唯一变量 A = prompt 是否含限长子句；唯一变量 B = n_predict 预算（128 vs 512）。
prompt 渲染与请求形状与产品同源（`/apply-template` + `/completion`，同 `LlamaCppClient.cs:121`）。

臂：
  J0    产品 prompt          , n_predict 512   （现网口径基线，本轮重跑）
  T2    产品 prompt + 限长子句, n_predict 512   （隔离 prompt 单独效应）
  T1    产品 prompt + 限长子句, n_predict 128   （候选配置）
  NC1t  T1 同配置 + prev 真错配（8 对，语料构建器机检 8/8）—— 非空心负控

字母解析 = `RelationLetterJudge.TryNormalize` 逐字重实现（源码派生）。增量落盘，中断不丢读数。
额外记账：落 `timings.prompt_n`，用于机检 `tokens_evaluated == prompt_n + cache_n`（闭合 R447 C5 未测项）。
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
R = ROOT / "eval/rover/r448"
CORPUS = R / "corpus.json"
PREREG = R / "prereg.json"
OUT = R / "probe-r448.json"
LOG = R / "server-r448.log"
PORT = int(os.environ.get("R448_PORT", "48481"))
BASE = f"http://127.0.0.1:{PORT}"
MODEL = "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
BIN = os.environ.get("AGENTFRAMEWORK_LLAMA_BIN",
                     "/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server")
SRV_ARGS_TAIL = ["-c", "4608", "-t", "1", "-np", "1", "--cache-type-k", "f32",
                 "--cache-type-v", "f32", "--flash-attn", "off", "--jinja"]
REF_R447 = ROOT / "eval/rover/r447/verdict-r447.json"     # 参照数字机读取值（禁手打）
PROC = None


def _load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def derive_literals():
    """system prompt / think 标记 / 字母正则 / conclusion 尾部长度：全部取自 C 源码。"""
    cm = _load_mod("cm_r444", ROOT / "eval/rover/r444/channel_marks.py")
    sysmsg = cm._const_of(cm.CS_JUDGE, "CorrectionJudgeSystem")
    src = (ROOT / "src/agent.modelqueue/LocalGenerationPort.cs").read_text(encoding="utf-8")

    def const(n):
        m = re.search(rf'public const string {n} = "((?:\\u[0-9a-fA-F]{{4}}|[^"])*)"', src)
        if not m:
            raise SystemExit(f"[致命] 源码常量未找到: {n}")
        return m.group(1).encode().decode("unicode_escape")

    m = re.search(r'Regex\.Matches\(text, @"([^"]+)"\)', src)
    rx = m.group(1) if m else r"(?<![A-Za-z])([CcAaNn])(?![A-Za-z])"
    tail = int(re.search(r"ConclusionTailChars = (\d+)", src).group(1))
    return {"system": sysmsg, "think_open": const("ThinkOpen"), "think_close": const("ThinkClose"),
            "letter_rx": rx, "conclusion_tail": tail}


def try_normalize(raw, L):
    if raw is None or not raw.strip():
        return None, "empty"
    text = raw.strip()
    close = text.rfind(L["think_close"])
    if close >= 0:
        text = text[close + len(L["think_close"]):]
    elif text.rfind(L["think_open"]) >= 0:
        return None, "thinking_truncated"
    elif len(text) > L["conclusion_tail"]:
        text = text[-L["conclusion_tail"]:]
    text = text.strip()
    if len(text) == 0:
        return None, "empty_conclusion"
    last, pick = -1, None
    for m in re.finditer(L["letter_rx"], text):
        last, pick = m.start(), m.group(1).upper()
    if last < 0:
        return None, "no_marker"
    return pick, "ok"


def post(path, body, timeout=1800):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def mem_available_mb():
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1024
    return -1


def start():
    global PROC
    if mem_available_mb() < 2650:
        raise SystemExit(f"[致命] 起手闸未过: MemAvailable={mem_available_mb()}MB < 2650MB")
    if not pathlib.Path(BIN).exists():
        raise SystemExit(f"[致命] llama-server 不存在: {BIN}")
    args = [BIN, "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT)] + SRV_ARGS_TAIL
    LOG.write_text("argv=" + json.dumps(args, ensure_ascii=False) + "\n", encoding="utf-8")
    PROC = subprocess.Popen(args, stdout=open(LOG, "a"), stderr=subprocess.STDOUT)
    t0 = time.time()
    while time.time() - t0 < 300:
        try:
            with urllib.request.urlopen(BASE + "/health", timeout=2) as r:
                if r.status == 200:
                    return args
        except Exception:
            time.sleep(2)
    raise SystemExit("[致命] llama-server 未就绪 (300s)")


def stop():
    if PROC:
        PROC.send_signal(signal.SIGTERM)
        try:
            PROC.wait(timeout=20)
        except Exception:
            PROC.kill()


def argv_selfproof(pid):
    raw = pathlib.Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    return [x.decode() for x in raw if x]


def render(prompt, L):
    return post("/apply-template", {"messages": [
        {"role": "system", "content": L["system"]},
        {"role": "user", "content": prompt}], "add_generation_prompt": True})["prompt"]


def complete(rendered, n_predict):
    body = {"prompt": rendered, "n_predict": n_predict, "temperature": 0.0,
            "samplers": ["temperature"], "cache_prompt": False, "stream": False,
            "return_tokens": True, "seed": 0}
    t0 = time.time()
    try:
        resp = post("/completion", body)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "wall_s": round(time.time() - t0, 3), "request": body}
    tm = resp.get("timings") or {}
    return {"content": resp.get("content"), "tokens_evaluated": resp.get("tokens_evaluated"),
            "timings_prompt_n": tm.get("prompt_n"), "gen": resp.get("tokens_predicted"),
            "cache_n": tm.get("cache_n"), "n_token_ids": len(resp.get("tokens") or []),
            "stop": resp.get("stop"), "wall_s": round(time.time() - t0, 3),
            "predicted_per_second": tm.get("predicted_per_second"),
            "prompt_per_second": tm.get("prompt_per_second"), "request": body}


ARMS = (("J0", 512), ("T2", 512), ("T1", 128))


def main():
    L = derive_literals()
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    prereg_bytes = PREREG.read_bytes()
    ref = json.loads(REF_R447.read_text(encoding="utf-8"))
    ref_cost = ref.get("cost") or {}
    ref_n = ref.get("n_pairs") or 18
    doc = {"round": "R448", "instrument": "r448_probe", "port": PORT,
           "prereg": {"path": "eval/rover/r448/prereg.json",
                      "sha256": hashlib.sha256(prereg_bytes).hexdigest(),
                      "mtime": PREREG.stat().st_mtime},
           "literals_from_source": L,
           "corpus_sha256": hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
           "ref_r447": {"gen_J0_sum": ref_cost.get("gen_J0_sum"), "n_pairs": ref_n,
                        "gen_mean_J0": (round(ref_cost["gen_J0_sum"] / ref_n, 2)
                                        if ref_cost.get("gen_J0_sum") else None),
                        "gen_J1_sum": ref_cost.get("gen_J1_sum"),
                        "wall_J0_mean": ref_cost.get("wall_J0_mean"),
                        "source": "eval/rover/r447/verdict-r447.json#cost（机读取值，禁手打）"},
           "pairs": [{k: p.get(k) for k in ("i", "msg", "prev", "archived_letter", "origin",
                                            "prompt_delta_chars")} for p in corpus["pairs"]],
           "arms": {}, "form": {}, "neg_form": {}}
    args = start()
    doc["form"]["argv"] = argv_selfproof(PROC.pid)
    doc["form"]["argv_expected_tail"] = SRV_ARGS_TAIL
    try:
        with urllib.request.urlopen(BASE + "/props", timeout=30) as r:
            doc["form"]["props"] = json.loads(r.read().decode())
    except Exception as e:
        doc["form"]["props_error"] = str(e)
    doc["form"]["server_log_argv"] = LOG.read_text(encoding="utf-8").splitlines()[:1]

    def flush():
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    flush()
    try:
        for p in corpus["pairs"]:
            i = p["i"]
            r_prod = render(p["prompt"], L)
            r_lim = render(p["prompt_limited"], L)
            if r_lim == r_prod:
                raise SystemExit(f"[致命] 限长 prompt 渲染后与产品 prompt 相同 ⇒ 变量未生效 i={i}")
            rec = {"msg": p["msg"], "prev": p["prev"], "archived_letter": p["archived_letter"],
                   "origin": p["origin"], "rendered_len_prod": len(r_prod),
                   "rendered_len_lim": len(r_lim), "calls": {}}
            for arm, npred in ARMS:
                rendered = r_prod if arm == "J0" else r_lim
                c = complete(rendered, npred)
                letter, reason = ((try_normalize(c.get("content"), L)) if "error" not in c
                                  else (None, "call_error"))
                c["letter"], c["parse_reason"] = letter, reason
                rec["calls"][arm] = c
                doc["arms"].setdefault(arm, []).append({**{k: c.get(k) for k in
                    ("content", "letter", "parse_reason", "tokens_evaluated", "timings_prompt_n",
                     "gen", "cache_n", "wall_s")}, "i": i, "msg": p["msg"]})
                flush()
                print(f"[{arm}] i={i} {p['msg']!r} letter={letter} reason={reason} gen={c.get('gen')} "
                      f"pe={c.get('tokens_evaluated')} wall={c.get('wall_s')}", flush=True)
            doc["arms"].setdefault("pairs_raw", []).append(rec)
            flush()

        for n in corpus["neg_control"]:
            k = n["i"]
            r_lim = render(n["prompt_limited"], L)
            c = complete(r_lim, 128)
            letter, reason = ((try_normalize(c.get("content"), L)) if "error" not in c
                              else (None, "call_error"))
            c["letter"], c["parse_reason"] = letter, reason
            doc["arms"].setdefault("NC1t", []).append({**{x: c.get(x) for x in
                ("content", "letter", "parse_reason", "tokens_evaluated", "timings_prompt_n",
                 "gen", "cache_n", "wall_s")}, "i": k, "msg": n["msg"],
                "prev": n["prev"], "prev_orig": n["prev_orig"]})
            doc["neg_form"].setdefault("rendered_len", []).append(len(r_lim))
            flush()
            print(f"[NC1t] i={k} {n['msg']!r} prev={n['prev'][:14]!r} prev_orig={n['prev_orig'][:14]!r} "
                  f"letter={letter} gen={c.get('gen')}", flush=True)
    finally:
        doc["form"]["mem_available_mb_after"] = mem_available_mb()
        flush()
        stop()
    print(f"[done] {OUT}", flush=True)


if __name__ == "__main__":
    main()
