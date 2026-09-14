#!/usr/bin/env python3
"""R411 取证: 多轮会话里渲染串是否被**重复计入**（独立实现对账: /apply-template + /tokenize）。

判据预注册（开跑前定, 事后只读结果）:
  P1 线性增长: tokens(turn2) - tokens(turn1) ≈ tokens(assistant) + tokens(user2) + 模板开销（≤ 40）
  P2 重复计入: tokens(turn2) ≥ 1.8 × tokens(turn1)  ⇒ 前缀被算了两遍
  P3 标记计数: 前缀首 30 字符在渲染串中出现的次数（>1 ⇒ 重复）
  P4 助手轮增量: tokens(turn3) - tokens(turn2) 同样应 ≤ 40
"""
import json
import os
import pathlib
import subprocess
import time
import urllib.request

BIN = os.environ.get("AGENTFRAMEWORK_LLAMA_BIN", "").replace("llama-server", "llama-server")
MODEL = "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
PREFIX = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r410/session-prefix.txt").read_text(encoding="utf-8")
PORT = 8941
BASE = f"http://127.0.0.1:{PORT}"
LOG = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r411/render_probe.log")

assert BIN and pathlib.Path(BIN).exists(), f"缺 llama-server: {BIN!r}"

proc = subprocess.Popen(
    [BIN, "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT), "-c", "6144",
     "-t", "2", "--cache-type-k", "f32", "--cache-type-v", "f32", "--flash-attn", "off", "--jinja"],
    stdout=LOG.open("wb"), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)


def post(path, body, timeout=120):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode("utf-8"),
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path, timeout=60):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


try:
    for _ in range(120):
        try:
            get("/health"); break
        except Exception:  # noqa: BLE001
            time.sleep(1)
    else:
        raise SystemExit("server 未就绪")

    marker = PREFIX[:30]
    a1, a2 = "用一句话回答: 1+1 等于几?", "用一句话回答: 2+2 等于几?"
    r1 = "<think>1+1=2</think>"
    msgs1 = [{"role": "system", "content": PREFIX}, {"role": "user", "content": a1}]
    msgs2 = msgs1 + [{"role": "assistant", "content": r1}, {"role": "user", "content": a2}]
    msgs3 = msgs2 + [{"role": "assistant", "content": "<think>2+2=4</think>"}, {"role": "user", "content": "用一句话回答: 3+3 等于几?"}]

    rows = []
    for name, msgs in (("turn1", msgs1), ("turn2", msgs2), ("turn3", msgs3)):
        p = post("/apply-template", {"messages": msgs})["prompt"]
        tk = post("/tokenize", {"content": p})["tokens"]
        rows.append({
            "arm": name, "chars": len(p), "tokens": len(tk),
            "marker_count": p.count(marker),
            "sha": __import__("hashlib").sha256(p.encode()).hexdigest()[:16],
        })

    print(f"前缀: {len(PREFIX)} 字符, 标记出现次数基准=1")
    for r in rows:
        print(f"  {r['arm']}: {r['chars']} 字符 {r['tokens']} token  标记x{r['marker_count']}  sha={r['sha']}")

    d12 = rows[1]["tokens"] - rows[0]["tokens"]
    d23 = rows[2]["tokens"] - rows[1]["tokens"]
    print(f"\nP1 线性增长: Δ(turn1→2)={d12} token (期望 ≤40)")
    print(f"P2 重复计入: turn2/turn1 = {rows[1]['tokens'] / rows[0]['tokens']:.2f}× (≥1.8 ⇒ 重复)")
    print(f"P3 标记计数: {[r['marker_count'] for r in rows]} (期望 全 1)")
    print(f"P4 助手轮增量: Δ(turn2→3)={d23} token (期望 ≤40)")
    verdict = {
        "linear_growth": d12 <= 40 and d23 <= 40,
        "duplicated": rows[1]["tokens"] >= 1.8 * rows[0]["tokens"] or any(r["marker_count"] > 1 for r in rows),
    }
    print(f"\n裁决: 线性增长={verdict['linear_growth']}  重复计入={verdict['duplicated']}")
    (pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r411/render-replay.json")).write_text(
        json.dumps({"rows": rows, "delta_1_2": d12, "delta_2_3": d23, "verdict": verdict}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
