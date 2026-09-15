#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R479 真机 E2E: 把**产品自建请求体字节**发到真端点, 存原始返回供产品语义函数离线判档。

口径:
  · 请求体字节 100% 由产品代码 (ResponsesWire.BuildRequest) 生成, 本脚本不重建、不修饰;
    远端通道仅替换 model 字段值 (通道参数, 显式记录)。
  · 真调用, 不模拟。凭据只从环境变量读, 不打印、不落盘。
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "/home/agentuser/AgentFramework/eval/rover/r479"
REQ = os.path.join(BASE, "requests")


def post(url, raw, headers):
    req = urllib.request.Request(url, data=raw, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # 传输层
        return -1, json.dumps({"transport": type(e).__name__, "msg": str(e)[:200]})


def usage_of(body):
    try:
        d = json.loads(body)
    except Exception:
        return {"unparsable": True}
    u = d.get("usage") or {}
    det = u.get("input_tokens_details") or {}
    out = {
        "present": bool(u),
        "input_tokens": u.get("input_tokens"),
        "cached_tokens": det.get("cached_tokens"),
        "output_tokens": u.get("output_tokens"),
        "reasoning_tokens": (u.get("output_tokens_details") or {}).get("reasoning_tokens"),
        "status": d.get("status"),
        "incomplete_reason": (d.get("incomplete_details") or {}).get("reason"),
        "item_types": [i.get("type") for i in (d.get("output") or []) if isinstance(i, dict)],
        "tool_names": [i.get("name") for i in (d.get("output") or [])
                       if isinstance(i, dict) and i.get("type") == "function_call"],
        "text_len": sum(len(c.get("text") or "")
                        for i in (d.get("output") or []) if isinstance(i, dict) and i.get("type") == "message"
                        for c in (i.get("content") or []) if isinstance(c, dict)),
    }
    return out


def save(name, status, body):
    path = os.path.join(BASE, name + ".raw.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return {"path": path, "bytes": len(body.encode("utf-8"))}


results = {}

# ---------- 本地 llama-server (/v1/responses) ----------
local = "http://127.0.0.1:8399/v1/responses"
hdr = {"Content-Type": "application/json"}
for tag, fn in (("answer", "request_answer.json"), ("tool", "request_tool.json")):
    raw = open(os.path.join(REQ, fn), "rb").read()
    st, body = post(local, raw, hdr)
    results["local_" + tag + "_1"] = {"http": st, "usage": usage_of(body), **save("e2e_local_" + tag + "_1", st, body)}
    if tag == "answer" and st == 200:
        st2, body2 = post(local, raw, hdr)  # 同字节连发 ⇒ 前缀缓存可见性
        results["local_answer_2"] = {"http": st2, "usage": usage_of(body2), **save("e2e_local_answer_2", st2, body2)}

# ---------- 远端 DeepSeek (/responses) ----------
key = os.environ.get("AGENTFRAMEWORK_KEYS_DEEPSEEK") or ""
if not key:
    results["remote"] = {"void": "key_missing_env"}
else:
    raw = open(os.path.join(REQ, "request_answer.json"), "rb").read()
    doc = json.loads(raw.decode("utf-8"))
    model_from_product = doc.get("model")
    doc["model"] = "deepseek-flash"  # 唯一替换: 通道参数 (显式记录)
    rraw = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    rhdr = {"Content-Type": "application/json", "Authorization": "Bearer " + key}
    st, body = post("https://api.deepseek.com/responses", rraw, rhdr)
    results["remote_answer_1"] = {"http": st, "model_from_product": model_from_product,
                                  "usage": usage_of(body), **save("e2e_remote_answer_1", st, body)}
    st2, body2 = post("https://api.deepseek.com/responses", rraw, rhdr)
    results["remote_answer_2"] = {"http": st2, "usage": usage_of(body2),
                                  **save("e2e_remote_answer_2", st2, body2)}

with open(os.path.join(BASE, "e2e_summary.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=1)

for k, v in results.items():
    print(k, "http=", v.get("http"), "usage=", json.dumps(v.get("usage"), ensure_ascii=False))
print("summary=", os.path.join(BASE, "e2e_summary.json"))
