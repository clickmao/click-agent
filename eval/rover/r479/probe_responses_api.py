#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R479 前置探针 —— DeepSeek /responses 真端点可用性 + usage 字段面(含 cached_tokens)。

生产级口径: 真 API 调用, 不模拟。同 input 连发 2 次以检验上下文缓存是否在 Responses
协议面**仍然可见**(承 R474-R477: 供应商 usage 为分母真值)。
key 只从环境变量读, 绝不落盘/打印。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

KEY = os.environ.get("AGENTFRAMEWORK_KEYS_DEEPSEEK") or ""
if not KEY:
    print(json.dumps({"void": "key_missing_env", "env": "AGENTFRAMEWORK_KEYS_DEEPSEEK"}, ensure_ascii=False))
    sys.exit(2)

URL = "https://api.deepseek.com/responses"
PREFIX = (
    "你是 click-agent 的判别子模块。以下为稳定的判别准则前缀, 用于检验上下文缓存可观测性。\n"
    + "\n".join(
        f"准则{i:02d}: 当上游 finish_reason 为 tool_calls 且正文为空时, 判因必须只取协议字段; "
        f"不得取用户文本关键词, 不得推测成因。示例载荷 {i:02d} = {{'finish_reason':'tool_calls','content':'','tool_calls':[{{'name':'read_file'}}]}}"
        for i in range(1, 61)
    )
)
TASK = "只回答两个字: 收到。"


def call(tag, n):
    body = {
        "model": "deepseek-flash",
        "instructions": "你是精确的判别器, 回答必须极简。",
        "input": [{"role": "user", "content": [{"type": "input_text", "text": PREFIX + "\n\n" + TASK}]}],
        "max_output_tokens": 16,
        "store": False,
        "stream": False,
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode("utf-8", "replace")
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        status = e.code
    dt = round(time.time() - t0, 2)
    out = {"tag": tag, "call": n, "http_status": status, "elapsed_s": dt}
    try:
        d = json.loads(raw)
    except Exception:
        out["raw_head"] = raw[:300]
        return out
    if status != 200:
        out["error"] = str(d)[:400]
        return out
    u = d.get("usage") or {}
    out["usage_raw_keys"] = sorted(u.keys())
    out["usage"] = {
        "input_tokens": u.get("input_tokens", u.get("prompt_tokens")),
        "cached_tokens": (u.get("input_tokens_details") or {}).get("cached_tokens", u.get("cached_tokens")),
        "output_tokens": u.get("output_tokens", u.get("completion_tokens")),
        "reasoning_tokens": (u.get("output_tokens_details") or {}).get("reasoning_tokens"),
        "total_tokens": u.get("total_tokens"),
    }
    out["resp_id_prefix"] = str(d.get("id"))[:24]
    out["top_keys"] = sorted(d.keys())
    items = d.get("output") or []
    out["output_item_types"] = [it.get("type") for it in items]
    out["text_head"] = "".join(
        c.get("text", "") for it in items for c in (it.get("content") or []) if it.get("type") == "message"
    )[:40]
    return out


res = [call("responses-api", 1), call("responses-api", 2)]
print(json.dumps({"endpoint": URL, "model": "deepseek-flash", "prefix_chars": len(PREFIX), "results": res}, ensure_ascii=False, indent=1))
