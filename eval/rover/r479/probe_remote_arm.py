#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R479 远端臂补跑: 产品自建请求体字节 → DeepSeek /responses (仅替换 model 通道参数)。

前台跑 (后台 shell 未继承凭据 env)。结果合并入 e2e_summary.json。
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "/home/agentuser/AgentFramework/eval/rover/r479"
key = os.environ.get("AGENTFRAMEWORK_KEYS_DEEPSEEK") or ""
if not key:
    print(json.dumps({"void": "key_missing_env", "checked_in": "foreground"}, ensure_ascii=False))
    sys.exit(2)

raw = open(os.path.join(BASE, "requests/request_answer.json"), "rb").read()
doc = json.loads(raw.decode("utf-8"))
model_from_product = doc.get("model")
doc["model"] = "deepseek-flash"
rraw = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
hdr = {"Content-Type": "application/json", "Authorization": "Bearer " + key}


def post():
    req = urllib.request.Request("https://api.deepseek.com/responses", data=rraw, headers=hdr, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, json.dumps({"transport": type(e).__name__, "msg": str(e)[:200]})


def summarize(body):
    try:
        d = json.loads(body)
    except Exception:
        return {"unparsable": True, "head": body[:200]}
    u = d.get("usage") or {}
    det = u.get("input_tokens_details") or {}
    return {"present": bool(u), "input_tokens": u.get("input_tokens"), "cached_tokens": det.get("cached_tokens"),
            "output_tokens": u.get("output_tokens"),
            "reasoning_tokens": (u.get("output_tokens_details") or {}).get("reasoning_tokens"),
            "status": d.get("status"), "item_types": [i.get("type") for i in (d.get("output") or []) if isinstance(i, dict)],
            "text_len": sum(len(c.get("text") or "") for i in (d.get("output") or []) if isinstance(i, dict)
                            and i.get("type") == "message" for c in (i.get("content") or []) if isinstance(c, dict))}


sp = os.path.join(BASE, "e2e_summary.json")
s = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {}
s.pop("remote", None)
for i in (1, 2):
    st, body = post()
    with open(os.path.join(BASE, "e2e_remote_answer_%d.raw.json" % i), "w", encoding="utf-8") as f:
        f.write(body)
    s["remote_answer_%d" % i] = {"http": st, "model_from_product": model_from_product, "usage": summarize(body)}
    print("remote_answer_%d" % i, "http=", st, json.dumps(s["remote_answer_%d" % i]["usage"], ensure_ascii=False))

json.dump(s, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("merged ->", sp)
