#!/usr/bin/env python3
"""R435 根因探针 — R434b 遗留候选①: 「J 判官本地化成功率 1/7」的根因 (raw 取证)。

背景 (已机检, 出处 eval/rover/r434/):
  - BRJ 臂 verdict: J 通道关系判官 7 次尝试中 **本地成功 1 / remote_fallback 6**。
  - 产品遥测 `correction_judge` (run-BRJ-p8-k1/data/telemetry/host.jsonl) 逐次留痕:
    6 次 source=remote_fallback (ms 6948–31233 = 本地失败后再走远端), 1 次 source=local (letter=N, 149 tok)。
  - 6 条 prompt 原文取自桩侧请求日志 `calls-BRJ-p8-k1.jsonl` (J 通道 = system=="只输出一个字母。") ⇒ **逐字忠实**。
    第 7 条 (`从头再说。`) 是唯一成功的那次, 按同构式重建 (prev=turn8 skip 回复, prompt_len=88 与 #1 逐位同构)。

本轮不猜「为什么失败」, 只做一件事: **把产品实发的 7 条 prompt 原样喂给 r1, 截 raw**。
  - 采样档与产品一致: temperature 0 / cache_prompt false / seed 0 / n_predict 512 / --jinja / f32 KV / flash-attn off / -np 1。
  - 判据 (预注册, 见 docs/plans/v0.56.0-r435-relation-judge-localization.md §4):
    J1a 至少 1 条 raw 复现「本地失败」(否则器具不可信, 停);
    J1b 失败归因落在**有限枚举**上: {think_truncated, no_letter_after_close, no_close_marker, empty};
    J1c 成功条 (`从头再说。`) 若在本器具下也失败 ⇒ 差异来自并发/时序而非 prompt ⇒ 归因换向。
输出: eval/rover/r435/probe-j1-raw.json (含逐条 raw 全文, 供人读)。
"""
import json, os, pathlib, signal, subprocess, sys, time, urllib.request

PORT = int(os.environ.get("R435_PORT", "47980"))
OUT = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r435")
MODEL = "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
BIN = os.environ.get("AGENTFRAMEWORK_LLAMA_BIN",
                     "/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server")
BASE = f"http://127.0.0.1:{PORT}"
LOG = open("/tmp/r435_server.log", "w")
THINK_CLOSE, THINK_OPEN = "<｜end▁of▁thinking｜>", " thinking"

# --- 产品实发 prompt 逐字复制 (calls-BRJ-p8-k1.jsonl J 通道) ---
P1 = "判定用户消息相对上一轮回答: 纠正否定上一轮=C, 认可采纳=A, 新话题无关=N。"
SKIP_REPLY = "收到，继续按当前方向推进，本轮不重新规划。"
STUB_REPLY = "桩应答: 收到, 已完成该步。"
CASES = [
    ("turn1", "", "把构建命令写成一行。", "untested_by_local?->fallback"),
    ("turn3", SKIP_REPLY, "再讲一遍。", "fallback"),
    ("turn5", STUB_REPLY, "讲细一点。", "fallback"),
    ("turn6", STUB_REPLY, "嗯嗯，知道了。", "fallback"),
    ("turn7", SKIP_REPLY, "换个说法。", "fallback"),
    ("turn8", STUB_REPLY, "明白，多谢。", "fallback"),
    ("turn9", SKIP_REPLY, "从头再说。", "local_ok"),
]
SYS = "只输出一个字母。"


def jprompt(prev, user):
    return f"{P1}\n上一轮: {prev}\n用户: {user}\n只输出一个字母。"


def post(path, body, timeout=1800):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def start():
    global PROC
    args = [BIN, "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT), "-c", "4608", "-t", "1",
            "-np", "1", "--cache-type-k", "f32", "--cache-type-v", "f32",
            "--flash-attn", "off", "--jinja"]
    print("[start]", " ".join(args), flush=True)
    PROC = subprocess.Popen(args, stdout=LOG, stderr=subprocess.STDOUT)
    for _ in range(180):
        try:
            with urllib.request.urlopen(BASE + "/health", timeout=2) as r:
                if r.status == 200:
                    print("[ready]", flush=True)
                    return True
        except Exception:
            time.sleep(1)
    return False


def stop():
    try:
        PROC.send_signal(signal.SIGTERM); PROC.wait(timeout=20)
    except Exception:
        try: PROC.kill()
        except Exception: pass


def classify(raw):
    """RelationLetterJudge.TryNormalize 的逐行忠实重实现 (LocalGenerationPort.cs:633-666)。"""
    import re
    if not raw or not raw.strip():
        return None, "empty"
    text = raw.strip()
    close = text.rfind(THINK_CLOSE)
    if close >= 0:
        text = text[close + len(THINK_CLOSE):]
        had_close = True
    else:
        had_close = False
        if text.rfind(THINK_OPEN) >= 0:
            return None, "think_truncated"
    text = text.strip()
    if not text:
        return None, ("empty_after_close" if had_close else "empty")
    last, pick = -1, None
    for m in re.finditer(r"(?<![A-Za-z])([CcAaNn])(?![A-Za-z])", text):
        last, pick = m.start(), m.group(1).upper()
    if last < 0:
        return None, "no_letter_after_close"
    return pick, "ok"


def main():
    if not pathlib.Path(BIN).exists():
        print("[致命] llama-server 不存在:", BIN); sys.exit(5)
    if not pathlib.Path(MODEL).exists():
        print("[致命] 模型不存在:", MODEL); sys.exit(9)
    OUT.mkdir(parents=True, exist_ok=True)
    if not start():
        print("[致命] 服务 180s 未就绪, 见 /tmp/r435_server.log"); sys.exit(4)
    try:
        props = post("/props", {}) if False else None
        try:
            with urllib.request.urlopen(BASE + "/props", timeout=10) as r:
                props = json.loads(r.read().decode())
        except Exception as e:
            props = {"error": str(e)}
        recs = []
        for name, prev, user, expect in CASES:
            p = jprompt(prev, user)
            turns = [{"role": "system", "content": SYS}, {"role": "user", "content": p}]
            rendered = post("/apply-template", {"messages": turns, "add_generation_prompt": True})["prompt"]
            body = {"prompt": rendered, "n_predict": 512, "temperature": 0.0,
                    "samplers": ["temperature"], "cache_prompt": False, "stream": False,
                    "return_tokens": True, "seed": 0}
            t0 = time.time()
            r = post("/completion", body)
            wall = round(time.time() - t0, 2)
            raw = r.get("content", "")
            letter, reason = classify(raw)
            t = r.get("timings", {}) or {}
            rec = {
                "case": name, "user": user, "prev_len": len(prev), "judge_prompt_len": len(p),
                "product_expect": expect,
                "rendered_prompt_len": len(rendered),
                "raw": raw, "raw_len": len(raw),
                "predicted_n": t.get("predicted_n"), "prompt_n": t.get("prompt_n"),
                "cache_n": t.get("cache_n"), "stop_type": r.get("stop_type"),
                "wall_s": wall,
                "has_think_close": THINK_CLOSE in raw, "has_think_open": THINK_OPEN in raw,
                "tail_after_close": (raw.rsplit(THINK_CLOSE, 1)[-1] if THINK_CLOSE in raw else raw)[-240:],
                "parsed_letter": letter, "parse_reason": reason,
            }
            recs.append(rec)
            print(f"[{name}] raw_len={rec['raw_len']} pred={rec['predicted_n']} stop={rec['stop_type']} "
                  f"close={rec['has_think_close']} -> letter={letter} reason={reason} wall={wall}s", flush=True)
            print("   tail:", repr(rec["tail_after_close"][:200]), flush=True)
        res = {"probe": "R435 J-judge local parseability (raw)",
               "bin": BIN, "model": MODEL, "server_args": {"c": 4608, "np": 1, "t": 1,
               "cache_type": "f32", "flash_attn": "off", "jinja": True},
               "decode": {"n_predict": 512, "temperature": 0.0, "cache_prompt": False, "seed": 0},
               "props": props, "cases": recs}
        (OUT / "probe-j1-raw.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        ok = sum(1 for c in recs if c["parse_reason"] == "ok")
        print(f"[done] parseable={ok}/{len(recs)}; raw -> {OUT/'probe-j1-raw.json'}", flush=True)
    finally:
        stop()


if __name__ == "__main__":
    main()
