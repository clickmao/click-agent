#!/usr/bin/env python3
"""R479: 本地 llama-server /v1/responses 真端点实测 (真调用, 不模拟)。
判据: 1) HTTP 码; 2) 出站 usage 字段面 (含 input_tokens_details.cached_tokens);
      3) 同 input 连发两次 -> cached_tokens 是否可观 (命中可见性);
      4) codex 风格 typed items 数组是否被接受; 5) prompt_cache_key 是否被接受。
"""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8399"
OUT = "/tmp/probe_r479_local.json"

TEXT = "用一句话说明什么是前缀缓存。"


def call(path, body):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}"


def pick(js, *keys):
    cur = js
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def text_of(js):
    out = js.get("output")
    if not isinstance(out, list):
        return None
    for item in out:
        if isinstance(item, dict) and item.get("type") == "message":
            for c in item.get("content") or []:
                if isinstance(c, dict) and c.get("type") == "output_text":
                    return c.get("text")
    return None


records = []

cases = [
    ("R1_string", "/v1/responses", {"model": "local", "input": TEXT,
                                    "max_output_tokens": 24, "store": False}),
    ("R2_string_same", "/v1/responses", {"model": "local", "input": TEXT,
                                         "max_output_tokens": 24, "store": False}),
    ("R3_items", "/v1/responses", {"model": "local", "input": [
        {"role": "user", "content": [{"type": "input_text", "text": TEXT}]}],
        "max_output_tokens": 24, "store": False}),
    ("R4_items_same", "/v1/responses", {"model": "local", "input": [
        {"role": "user", "content": [{"type": "input_text", "text": TEXT}]}],
        "max_output_tokens": 24, "store": False}),
    ("R5_cachekey", "/v1/responses", {"model": "local", "input": TEXT,
                                      "max_output_tokens": 16, "store": False,
                                      "prompt_cache_key": "r479"}),
    ("R6_prevresp", "/v1/responses", {"model": "local", "input": TEXT,
                                      "max_output_tokens": 16,
                                      "previous_response_id": "resp_x"}),
    ("C1_completion", "/completion", {"prompt": TEXT, "n_predict": 8,
                                      "temperature": 0, "cache_prompt": True}),
    ("C2_completion_same", "/completion", {"prompt": TEXT, "n_predict": 8,
                                           "temperature": 0, "cache_prompt": True}),
]

for name, path, body in cases:
    code, raw = call(path, body)
    rec = {"case": name, "path": path, "http": code}
    try:
        js = json.loads(raw)
    except Exception:  # noqa: BLE001
        rec["parse_error"] = True
        rec["body_head"] = raw[:300]
        records.append(rec)
        print(f"{name:16s} http={code} NON_JSON {raw[:120]!r}")
        continue
    rec["top_keys"] = sorted(js.keys())
    rec["object"] = js.get("object")
    rec["id"] = js.get("id")
    rec["status"] = js.get("status")
    rec["usage"] = js.get("usage")
    rec["text"] = text_of(js) if path.endswith("responses") else None
    if path == "/completion":
        rec["timings"] = js.get("timings")
        rec["tokens_cached"] = js.get("tokens_cached")
        rec["prompt_n"] = js.get("prompt_n") if "prompt_n" in js else pick(js, "timings", "prompt_n")
        rec["text"] = (js.get("content") or "")[:80]
    records.append(rec)
    u = rec["usage"] or {}
    cached = pick(u, "input_tokens_details", "cached_tokens")
    print(f"{name:16s} http={code} obj={rec['object']} in={u.get('input_tokens')} "
          f"out={u.get('output_tokens')} cached={cached} "
          f"err={(js.get('error') or {}).get('message') if isinstance(js.get('error'), dict) else js.get('error')}")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=1)
print("saved:", OUT, len(records), "records")
