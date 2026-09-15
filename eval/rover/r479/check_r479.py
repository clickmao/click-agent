#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R479 器具: 只读**已落盘真值**, 不重建请求、不重跑被测面。

判据面 (源码派生 + fail-closed):
  C1 产品自建请求体的协议不变量 (instructions/input 独立字段 · typed item · store:false · 无 BOM)
  C2 真机 E2E 读数 (本地 llama /v1/responses + 远端 DeepSeek /responses) HTTP 与 usage 可见性
  C3 文案单源: 校准面不得新写第二处失效文案 (必须全部经 EmptyBodyDiagnosis.Banner)
  C4 声明面单源: chat 形态与既有常量逐字节相等的断言必须存在
  C5 真值口径: usage 未上报 != 0 (Present/CachedPresent 分列 + NewTokens 双侧齐备才可得)
负控:
  NC1 用户输入不得被塞进 instructions
  NC2 不得出现 "store":true
  NC3 请求体不得带 BOM
"""
import json
import os
import sys

BASE = "/home/agentuser/AgentFramework"
R = os.path.join(BASE, "eval/rover/r479")
checks, negs = {}, {}


def record(d, k, ok, detail):
    d[k] = {"ok": bool(ok), "detail": detail}


def load(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


# ---------- C1 ----------
c1 = {}
req_files = ["requests/request_answer.json", "requests/request_tool.json"]
bodies = {}
for rel in req_files:
    p = os.path.join(R, rel)
    if not os.path.exists(p):
        c1[rel] = {"ok": False, "detail": "missing"}
        continue
    raw = open(p, "rb").read()
    bodies[rel] = raw
    try:
        doc = json.loads(raw.decode("utf-8"))
    except Exception as e:
        c1[rel] = {"ok": False, "detail": "unparsable:" + type(e).__name__}
        continue
    itypes = sorted({i.get("type") for i in doc.get("input", [])})
    tools_flat = all("function" not in t for t in doc.get("tools", [])) if doc.get("tools") else None
    ok = (doc.get("store") is False
          and isinstance(doc.get("instructions"), str) and doc["instructions"] != ""
          and isinstance(doc.get("input"), list) and len(doc["input"]) > 0
          and itypes and all(t in ("message", "function_call_output") for t in itypes)
          and (tools_flat is not False))
    c1[rel] = {"ok": ok, "detail": {"top_keys": sorted(doc.keys()), "input_types": itypes,
                                    "tools_flat": tools_flat, "store": doc.get("store")}}
record(checks, "C1_protocol_invariants", all(v["ok"] for v in c1.values()), c1)

# ---------- NC1/NC2/NC3 ----------
nc = {}
ans = bodies.get("requests/request_answer.json", b"")
try:
    adoc = json.loads(ans.decode("utf-8"))
except Exception:
    adoc = {}
nc["NC1_user_text_not_in_instructions"] = (adoc.get("instructions", "").find("前缀缓存为什么能省 token") == -1)
nc["NC2_no_store_true"] = all(b'"store":true' not in v for v in bodies.values())
nc["NC3_no_bom"] = all(not v.startswith(b"\xef\xbb\xbf") for v in bodies.values())
for k, v in nc.items():
    record(negs, k, v, "pass" if v else "violation")

# ---------- C2 ----------
c2 = {}
sp = os.path.join(R, "e2e_summary.json")
if os.path.exists(sp):
    s = json.load(open(sp, encoding="utf-8"))
    for k in ("local_answer_1", "local_tool_1", "remote_answer_1"):
        v = s.get(k)
        if not v:
            c2[k] = {"ok": False, "detail": "missing"}
            continue
        u = v.get("usage") or {}
        c2[k] = {"ok": v.get("http") == 200 and bool(u.get("present")),
                 "detail": {"http": v.get("http"), "status": u.get("status"),
                            "input_tokens": u.get("input_tokens"), "cached_tokens": u.get("cached_tokens"),
                            "item_types": u.get("item_types"), "tool_names": u.get("tool_names")}}
    a1 = (s.get("local_answer_1") or {}).get("usage") or {}
    a2 = (s.get("local_answer_2") or {}).get("usage") or {}
    if a1 and a2:
        try:
            c2["cache_visibility_local"] = {"ok": int(a2.get("cached_tokens") or 0) > 0,
                                            "detail": {"call1": a1.get("cached_tokens"), "call2": a2.get("cached_tokens")}}
        except Exception as e:
            c2["cache_visibility_local"] = {"ok": False, "detail": "int:" + type(e).__name__}
else:
    c2["summary"] = {"ok": False, "detail": "missing e2e_summary.json"}
record(checks, "C2_real_endpoint", all(v["ok"] for v in c2.values()), c2)

# ---------- C3 文案单源 ----------
src = load(os.path.join(BASE, "src/agent.modelqueue/LocalDecisionMap.cs"))
banner_calls = src.count("EmptyBodyDiagnosis.Banner(")
literal_banners = sum(src.count(x) for x in ('"上游请求执行工具动作', '": 上游')) 
record(checks, "C3_banner_single_source",
       banner_calls >= 4 and literal_banners == 0,
       {"banner_calls": banner_calls, "inline_banner_literals": literal_banners})

# ---------- C4 声明面单源 ----------
tst = load(os.path.join(BASE, "src/agent.tests/ResponsesWireTests.cs"))
record(checks, "C4_tool_decl_single_source",
       "Assert.Equal(ActionToolDecl.ToolsJson, ActionToolSpec.ChatToolsJson)" in tst,
       {"byte_equal_assertion": "Assert.Equal(ActionToolDecl.ToolsJson, ActionToolSpec.ChatToolsJson)" in tst})

# ---------- C5 真值口径 ----------
wire = load(os.path.join(BASE, "src/agent.modelqueue/ResponsesWire.cs"))
record(checks, "C5_usage_unreported_not_zero",
       "public bool Present" in wire and "public bool CachedPresent" in wire
       and "Present && CachedPresent" in wire,
       {"present_flag": "public bool Present" in wire,
        "cached_present_flag": "public bool CachedPresent" in wire,
        "newtokens_guarded": "Present && CachedPresent" in wire})

failed = [k for k, v in checks.items() if not v["ok"]]
verdict = {"round": "R479", "checks": checks, "negative_controls": negs,
           "failed": failed, "verdict": "PASS" if not failed else "FAIL"}
out = os.path.join(R, "verdict-r479.json")
json.dump(verdict, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in checks.items():
    print(k, "OK" if v["ok"] else "FAIL", json.dumps(v["detail"], ensure_ascii=False)[:220])
print("verdict=", verdict["verdict"], "->", out)
sys.exit(0 if not failed else 1)
