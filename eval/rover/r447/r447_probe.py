#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R447 真机探针：判官解码侧约束（单字母 GBNF）的等价性与收益。

预注册判据见 eval/rover/r447/prereg.json（**先落盘**；本器具把它的 sha256/mtime 写进结果供核对）。
唯一变量 = 解码约束；prompt 与采样档逐字不变（`/apply-template` 渲染 + `/completion`，与
`src/agent.llamacpp/LlamaCppClient.cs:121` 同一实发形状）。

臂：
  J0  基线（无 grammar, n_predict 512）          —— 现网口径参考
  J1  语法单字母（grammar 'root ::= "A"|"C"|"N"', n_predict 8）
  J2  仅短预算（无 grammar, n_predict 8）        —— 反证「只砍预算」不可行
  NC1 错配 prev（prev 换成 i+1 的 prev，其余同 J0）—— 器具非空心负控（前 8 对）

字母解析 = `RelationLetterJudge.TryNormalize` 的**逐字重实现**（源码派生，禁手打）：
  LocalGenerationPort.cs:690-733 + ThinkOpen/ThinkClose(:434-435)。
增量落盘：每请求后重写 probe-r447.json（超时/中断不丢已测读数）。
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
R = ROOT / "eval/rover/r447"
CORPUS = R / "corpus.json"
PREREG = R / "prereg.json"
OUT = R / "probe-r447.json"
LOG = R / "server-r447.log"
PORT = int(os.environ.get("R447_PORT", "47981"))
BASE = f"http://127.0.0.1:{PORT}"
MODEL = "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
BIN = os.environ.get("AGENTFRAMEWORK_LLAMA_BIN",
                     "/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server")
SRV_ARGS_TAIL = ["-c", "4608", "-t", "1", "-np", "1", "--cache-type-k", "f32",
                 "--cache-type-v", "f32", "--flash-attn", "off", "--jinja"]
GRAMMAR = 'root ::= "A" | "C" | "N"'
N_NEG = 8
PROC = None


# ───────────────────────── 源码派生（禁手打） ─────────────────────────
def _load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def derive_literals():
    """system prompt / think 标记 / 字母正则 全部从 C 源码取，不手打。"""
    cm = _load_mod("cm_r444", ROOT / "eval/rover/r444/channel_marks.py")
    sysmsg = cm._const_of(cm.CS_JUDGE, "CorrectionJudgeSystem")
    src = (ROOT / "src/agent.modelqueue/LocalGenerationPort.cs").read_text(encoding="utf-8")
    def const(n):
        m = re.search(rf'public const string {n} = "((?:\\u[0-9a-fA-F]{{4}}|[^"])*)"', src)
        if not m:
            raise SystemExit(f"[致命] 源码常量未找到: {n}")
        return m.group(1).encode().decode("unicode_escape")
    # 结论区字母正则 (:719) —— 从源码字面量取
    m = re.search(r'Regex\.Matches\(text, @"([^"]+)"\)', src)
    rx = m.group(1) if m else r"(?<![A-Za-z])([CcAaNn])(?![A-Za-z])"
    tail = int(re.search(r"ConclusionTailChars = (\d+)", src).group(1))
    words = re.search(r"ConclusionWords =\s*\n?\s*(System\.Array\.Empty[^;]*;|\[[^\]]*\])", src)
    return {"system": sysmsg, "think_open": const("ThinkOpen"), "think_close": const("ThinkClose"),
            "letter_rx": rx, "conclusion_tail": tail,
            "conclusion_words_src": (words.group(1).strip() if words else None)}


def try_normalize(raw, L):
    """RelationLetterJudge.TryNormalize 逐字重实现（返回 (letter|None, reason)）。"""
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
    # ConclusionWords() 现网为**空表**（源码 `System.Array.Empty`），故无词表分支
    if last < 0:
        return None, "no_marker"
    return pick, "ok"


# ───────────────────────── HTTP / 进程 ─────────────────────────
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


# ───────────────────────── 主流程 ─────────────────────────
def render(prompt, L):
    return post("/apply-template", {"messages": [
        {"role": "system", "content": L["system"]},
        {"role": "user", "content": prompt}], "add_generation_prompt": True})["prompt"]


def complete(rendered, n_predict, grammar=None):
    body = {"prompt": rendered, "n_predict": n_predict, "temperature": 0.0,
            "samplers": ["temperature"], "cache_prompt": False, "stream": False,
            "return_tokens": True, "seed": 0}
    if grammar:
        body["grammar"] = grammar
    t0 = time.time()
    try:
        resp = post("/completion", body)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "wall_s": round(time.time() - t0, 3), "request": body}
    tm = resp.get("timings") or {}
    return {
        "content": resp.get("content"),
        "prompt_n": resp.get("tokens_evaluated"),
        "gen": resp.get("tokens_predicted"),
        "cache_n": tm.get("cache_n"),
        "n_token_ids": len(resp.get("tokens") or []),
        "stop": resp.get("stop"),
        "wall_s": round(time.time() - t0, 3),
        "predicted_per_second": tm.get("predicted_per_second"),
        "prompt_per_second": tm.get("prompt_per_second"),
        "request": body,
    }


def main():
    L = derive_literals()
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    prereg_bytes = PREREG.read_bytes()
    doc = {
        "round": "R447", "instrument": "r447_probe", "port": PORT,
        "prereg": {"path": "eval/rover/r447/prereg.json",
                   "sha256": hashlib.sha256(prereg_bytes).hexdigest(),
                   "mtime": PREREG.stat().st_mtime},
        "literals_from_source": L,
        "corpus_sha256": hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
        "pairs": corpus["pairs"], "arms": {}, "form": {},
    }
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
        # 主循环：每对样本 渲染一次 → J0/J1/J2
        for p in corpus["pairs"]:
            i = p["i"]
            rendered = render(p["prompt"], L)
            rec = {"msg": p["msg"], "prev": p["prev"], "prompt_len": p["prompt_len"],
                   "rendered_len": len(rendered), "archived_letter": p["archived_letter"],
                   "origin": p["origin"], "calls": {}}
            for arm, grammar, npred in (("J0", None, 512), ("J1", GRAMMAR, 8), ("J2", None, 8)):
                c = complete(rendered, npred, grammar)
                letter, reason = (try_normalize(c.get("content"), L) if "error" not in c else (None, "call_error"))
                c["letter"], c["parse_reason"] = letter, reason
                rec["calls"][arm] = c
                doc["arms"].setdefault(arm, []).append({**{k: c.get(k) for k in
                    ("content", "letter", "parse_reason", "prompt_n", "gen", "cache_n", "wall_s")},
                    "i": i, "msg": p["msg"]})
                flush()
                print(f"[{arm}] i={i} {p['msg']!r} letter={letter} reason={reason} "
                      f"gen={c.get('gen')} prompt_n={c.get('prompt_n')} wall={c.get('wall_s')}", flush=True)
            doc["arms"].setdefault("pairs_raw", []).append(rec)
            flush()

        # NC1 错配 prev（前 N_NEG 对，prev 取 i+1 的 prev）
        n = len(corpus["pairs"])
        mod = _load_mod("r447_corpus", R / "r447_corpus.py")
        tpl = mod.derive_prompt_template()      # 分隔符同样源码派生（禁手打）
        for k in range(min(N_NEG, n)):
            p = corpus["pairs"][k]
            wrong_prev = corpus["pairs"][(k + 1) % n]["prev"]
            q = mod.build_prompt(tpl, wrong_prev, p["msg"])
            rendered = render(q, L)
            c = complete(rendered, 512, None)
            letter, reason = (try_normalize(c.get("content"), L) if "error" not in c else (None, "call_error"))
            c["letter"], c["parse_reason"] = letter, reason
            doc["arms"].setdefault("NC1", []).append({**{k2: c.get(k2) for k2 in
                ("content", "letter", "parse_reason", "prompt_n", "gen", "cache_n", "wall_s")},
                "i": k, "msg": p["msg"], "prev": wrong_prev, "prev_orig": p["prev"]})
            flush()
            print(f"[NC1] i={k} {p['msg']!r} wrong_prev={wrong_prev[:12]!r} letter={letter} gen={c.get('gen')}", flush=True)
    finally:
        doc["form"]["mem_available_mb_after"] = mem_available_mb()
        flush()
        stop()
    print(f"[done] {OUT}", flush=True)


if __name__ == "__main__":
    main()
