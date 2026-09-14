#!/usr/bin/env python3
"""R410 探针 v2: 本地通路 K2b「可复用前缀覆盖率」实测（分臂增量落盘）。

v1 教训: ①单线程 prefill 实测 26 t/s ⇒ 4800 token 一遍 185 s，四臂串行必超时；
        ②只在末尾写 JSON ⇒ 被掐断则零证据。故本版: 前缀压到刚过红线(>=4224)、每臂立刻落盘。

判据（预注册，先注册后测）:
  J1 会话形态（长前缀 + user）第 2 次同前缀请求: cache_n / prompt_n >= 0.97
  J2 短独立 prompt（R409 权威 96B 形状）: 绝对 cache_n << 4224（结构上不达标）
  J3 负控（前缀首 token 改变）: cache_n 必须归零
  J4 cache_prompt=false: cache_n 必须恒为 0（⇒ 对账口径与生产口径必须分离）
读数来源: llama-server /completion 的 timings.cache_n / timings.prompt_n（服务端自报）。
"""
import json
import pathlib
import time
import urllib.request

BASE = "http://127.0.0.1:8933"
REQUIRED_PREFIX = 4224
OUT = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r410")
OUT.mkdir(parents=True, exist_ok=True)
RESULT = OUT / "prefix-reuse.json"
state = {"base": BASE, "required_prefix_tokens": REQUIRED_PREFIX, "arms": {}}


def flush():
    RESULT.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def post(path, body, timeout=1800):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def tokenize(text, add_special=True):
    return post("/tokenize", {"content": text, "add_special": add_special})["tokens"]


def render(messages):
    return post("/apply-template", {"messages": messages, "add_generation_prompt": True})["prompt"]


def complete(prompt, cache_prompt=True, n_predict=1):
    t0 = time.time()
    r = post("/completion", {
        "prompt": prompt, "n_predict": n_predict, "temperature": 0.0,
        "samplers": ["temperature"], "cache_prompt": cache_prompt, "stream": False})
    t = r.get("timings") or {}
    return {"prompt_n": t.get("prompt_n"), "cache_n": t.get("cache_n", t.get("tokens_cached")),
            "prompt_ms": t.get("prompt_ms"), "wall_ms": round((time.time() - t0) * 1000, 1)}


def arm(name, prompt, cache_prompt=True):
    t0 = time.time()
    m = complete(prompt, cache_prompt=cache_prompt)
    m["arm"] = name
    m["cache_prompt"] = cache_prompt
    m["elapsed_s"] = round(time.time() - t0, 1)
    state["arms"][name] = m
    flush()
    print(f"[arm] {name:28s} prompt_n={m['prompt_n']} cache_n={m['cache_n']} wall={m['elapsed_s']}s", flush=True)
    return m


# ---- 造长前缀（按块 token 数算次数，避免反复 tokenize 大串）----
block = "你是本地执行代理。以下为常驻上下文：项目约定、工具清单、历史摘要与验收标准。\n"
bt = len(tokenize(block))
reps = (REQUIRED_PREFIX + 200) // bt + 1
sysmsg = block * reps
state["system_prefix_tokens"] = len(tokenize(sysmsg))
state["block_tokens"] = bt
state["block_reps"] = reps
flush()
print("system 前缀 token:", state["system_prefix_tokens"], f"(block={bt} x {reps})", flush=True)

J = "2+2=?"
P1 = render([{"role": "system", "content": sysmsg}, {"role": "user", "content": "1+1=?"}])
P2 = render([{"role": "system", "content": sysmsg}, {"role": "user", "content": J}])
P3 = render([{"role": "system", "content": "X" + sysmsg}, {"role": "user", "content": J}])
state["prompt_tokens"] = {"P1": len(tokenize(P1)), "P2": len(tokenize(P2)), "P3": len(tokenize(P3))}
flush()
print("P1/P2/P3 token:", state["prompt_tokens"], flush=True)

N2 = state["prompt_tokens"]["P2"]
cold = arm("session_cold", P1)
warm = arm("session_warm_same_prefix", P2)
off = arm("session_cache_off", P2, cache_prompt=False)
neg = arm("negative_prefix_first_token_changed", P3)

short = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r409/prompt.txt").read_text()
s1 = arm("short_cold", short)
s2 = arm("short_warm", short)

wr = (warm["cache_n"] or 0) / N2
state["verdict"] = {
    "warm_reuse_ratio": round(wr, 4),
    "J1_session_reuse_ge_097": wr >= 0.97,
    "J2_short_absolute_cache_n": s2["cache_n"],
    "J2_short_coverage_of_required": round((s2["cache_n"] or 0) / REQUIRED_PREFIX, 5),
    "J2_short_structurally_below_required": (s2["cache_n"] or 0) < REQUIRED_PREFIX,
    "J3_negative_cache_zero": (neg["cache_n"] or 0) == 0,
    "J4_cache_off_zero": (off["cache_n"] or 0) == 0,
    "session_prefix_meets_required": state["system_prefix_tokens"] >= REQUIRED_PREFIX,
}
flush()
print("判定:", json.dumps(state["verdict"], ensure_ascii=False, indent=1), flush=True)
