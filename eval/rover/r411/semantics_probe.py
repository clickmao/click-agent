#!/usr/bin/env python3
"""R411 语义探针（独立实现，不经过产品代码）: 钉死 /completion 三个字段的含义。

同一条消息列表 + 同一条渲染串，直连服务端两次请求：
  第 1 次（冷）与第 2 次（热）分别读 tokens_evaluated / timings.prompt_n / timings.cache_n，
  并与独立测得的渲染串 token 数（/apply-template + /tokenize）对照。

判据预注册:
  A. tokens_evaluated == 渲染串 token 数（⇒ 它是**总长**，不是新评估数）
  B. tokens_evaluated == timings.prompt_n + timings.cache_n（⇒ 它是总长，prompt_n 才是新评估数）
  C. 二者只能成立一个；都不成立 ⇒ 记为未知，不许硬套。
"""
import hashlib
import json
import os
import pathlib
import subprocess
import time
import urllib.request

BIN = os.environ.get("AGENTFRAMEWORK_LLAMA_BIN", "")
MODEL = "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
D = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r411")
PREFIX = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r410/session-prefix.txt").read_text(encoding="utf-8")
PORT = 8942
BASE = f"http://127.0.0.1:{PORT}"
LOG = D / "semantics_probe.log"
assert BIN and pathlib.Path(BIN).exists(), f"缺 llama-server: {BIN!r}"

proc = subprocess.Popen(
    [BIN, "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT), "-c", "6144",
     "-t", "2", "--cache-type-k", "f32", "--cache-type-v", "f32", "--flash-attn", "off", "--jinja"],
    stdout=LOG.open("wb"), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)


def post(path, body, timeout=300):
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

    a1 = "用一句话回答: 1+1 等于几?"
    a2 = "用一句话回答: 2+2 等于几?"
    msgs1 = [{"role": "system", "content": PREFIX}, {"role": "user", "content": a1}]
    gen = {"n_predict": 16, "temperature": 0, "cache_prompt": True, "top_k": 1, "top_p": 1.0, "min_p": 0.0, "repeat_penalty": 1.0}

    rows = []
    reply1 = None
    for arm, msgs in (("cold", msgs1),):
        p = post("/apply-template", {"messages": msgs})["prompt"]
        tk = len(post("/tokenize", {"content": p})["tokens"])
        r = post("/completion", dict(gen, prompt=p))
        reply1 = r["content"]
        rows.append({"arm": arm, "render_tokens": tk, "tokens_evaluated": r["tokens_evaluated"],
                     "timings_prompt_n": r["timings"]["prompt_n"], "cache_n": r["timings"]["cache_n"],
                     "content": reply1})

    msgs2 = msgs1 + [{"role": "assistant", "content": reply1}, {"role": "user", "content": a2}]
    p2 = post("/apply-template", {"messages": msgs2})["prompt"]
    tk2 = len(post("/tokenize", {"content": p2})["tokens"])
    r2 = post("/completion", dict(gen, prompt=p2))
    rows.append({"arm": "warm", "render_tokens": tk2, "tokens_evaluated": r2["tokens_evaluated"],
                 "timings_prompt_n": r2["timings"]["prompt_n"], "cache_n": r2["timings"]["cache_n"],
                 "content": r2["content"]})

    for x in rows:
        print(f"{x['arm']:5s}: 渲染串={x['render_tokens']:5d} tok | tokens_evaluated={x['tokens_evaluated']:5d} "
              f"| timings.prompt_n={x['timings_prompt_n']:5d} | cache_n={x['cache_n']:5d}")

    A = all(x["tokens_evaluated"] == x["render_tokens"] for x in rows)
    B = all(x["tokens_evaluated"] == x["timings_prompt_n"] + x["cache_n"] for x in rows)
    print(f"\nA tokens_evaluated == 渲染串总长 : {A}")
    print(f"B tokens_evaluated == prompt_n + cache_n (= 总长重建) : {B}")
    hot = rows[-1]
    eff = hot["cache_n"] / hot["render_tokens"] if hot["render_tokens"] else -1
    print(f"热轮: 命中 {hot['cache_n']} / 总长 {hot['render_tokens']} = {eff:.4f}  (97% 红线)")
    verdict = {"A_total": A, "B_reconstruct": B, "warm_hit": hot["cache_n"], "warm_total": hot["render_tokens"], "warm_eff": round(eff, 4)}
    (D / "semantics.json").write_text(json.dumps({"rows": rows, "verdict": verdict}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n裁决写入 {D / 'semantics.json'}")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
