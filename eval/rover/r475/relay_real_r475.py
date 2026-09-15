#!/usr/bin/env python3
"""R475 真实转发中继 v2 — 在 R474 中继基础上补「空正文可定因」证据面 + 采样参数面。

为什么另起文件而不改 R474 器具: R474 的 relay_real.py sha 已**绑定**在登记表/报告里
(Q25/Q26 的教训: 证据 ↔ 器具版本必须绑定, 改器具 = 证据降级) ⇒ 硬化版另存新器具、新 sha。

相对 v1 的**只增**字段:
  请求面 calls-<tag>.jsonl : + `sampling` (temperature / max_tokens / top_p / penalties /
                             stream / response_format / tools_n)  —— R474 未落盘采样参数,
                             空正文无法定因 (是被 max_tokens 截断? 还是被温度/推理预算吃光?)
  读数面 usage-<tag>.jsonl : + `finish_reason` / `choices_n` / `content_len` /
                             `reasoning_len` / `reasoning_tokens` / `empty_body` /
                             `body_head` (仅非 200 时, 截断 300 字符, 不含 key)
  恒等式: 每次转发都断言 `prompt_tokens == hit + miss` 并把结论落盘 (`identity_ok`),
          不成立 ⇒ 该行 `identity_ok=false` (禁静默)。

不动: 预算闸 (调用数 + 成本上界, 越限 402 fail-closed)、凭据卫生 (只读 env, 不落盘)。
用法: python3 -u relay_real_r475.py <port> <max_calls> <max_cny> <outdir> <tag> [upstream_url]
"""
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
MAX_CALLS = int(sys.argv[2])
MAX_CNY = float(sys.argv[3])
OUTDIR = sys.argv[4]
TAG = sys.argv[5]
UPSTREAM = sys.argv[6] if len(sys.argv) > 6 else os.environ.get(
    "R475_UPSTREAM", "https://api.deepseek.com/v1/chat/completions")
KEY = os.environ.get("R475_UPSTREAM_KEY", "")
PRICE_IN_PER_M = 0.27      # config/base/models.yaml deepseek-flash（缓存命中未折价 ⇒ 成本上界）
PRICE_OUT_PER_M = 1.10

CALLS_PATH = os.path.join(OUTDIR, "calls-%s.jsonl" % TAG)
USAGE_PATH = os.path.join(OUTDIR, "usage-%s.jsonl" % TAG)
LOCK = threading.Lock()
STATE = {"n": 0, "cost_upper": 0.0, "blocked": 0, "prompt": 0, "completion": 0,
         "hit": 0, "miss": 0, "empty_body": 0, "identity_bad": 0}


def est_tokens_from_messages(msgs):
    """与 eval/rover/r430/stub_openai.py 同口径 (字符数//2), 只为与桩臂可比, 显式标注为估算。"""
    chars = 0
    for m in msgs:
        ct = m.get("content")
        if isinstance(ct, str):
            chars += len(ct)
        elif isinstance(ct, list):
            for part in ct:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    chars += len(part["text"])
    return max(1, chars // 2)


def sampling_of(body):
    """R475: 采样参数面 —— 与「空正文」定因直接相关, 逐字段显式取值 (缺 ⇒ null, 不猜)。"""
    rf = body.get("response_format")
    return {
        "model": body.get("model"),
        "temperature": body.get("temperature"),
        "max_tokens": body.get("max_tokens"),
        "top_p": body.get("top_p"),
        "presence_penalty": body.get("presence_penalty"),
        "frequency_penalty": body.get("frequency_penalty"),
        "stream": bool(body.get("stream")),
        "reasoning_effort": body.get("reasoning_effort"),
        "thinking": body.get("thinking") if isinstance(body.get("thinking"), dict) else None,
        "response_format_type": (rf or {}).get("type") if isinstance(rf, dict) else None,
        "tools_n": len(body.get("tools") or []),
    }


def choices_facts(payload):
    """R475: 从响应体取「空正文」定因三件事 —— 结束原因 / 正文长度 / 推理长度。"""
    out = {"finish_reason": None, "choices_n": 0, "content_len": 0,
           "reasoning_len": 0, "reasoning_tokens": None, "empty_body": None}
    try:
        obj = json.loads(payload or b"{}") or {}
    except Exception:
        return out
    ch = obj.get("choices") or []
    out["choices_n"] = len(ch)
    if ch and isinstance(ch[0], dict):
        c0 = ch[0]
        out["finish_reason"] = c0.get("finish_reason")
        msg = c0.get("message") or {}
        content = msg.get("content")
        out["content_len"] = len(content) if isinstance(content, str) else 0
        for key in ("reasoning_content", "reasoning"):
            v = msg.get(key)
            if isinstance(v, str) and v:
                out["reasoning_len"] = len(v)
                break
    u = obj.get("usage") or {}
    rt = u.get("completion_tokens_details")
    if isinstance(rt, dict) and rt.get("reasoning_tokens") is not None:
        out["reasoning_tokens"] = rt.get("reasoning_tokens")
    if out["choices_n"]:
        out["empty_body"] = out["content_len"] == 0
    return out


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/health"):
            self._json(200, {"ok": True, "calls": STATE["n"], "cost_upper": STATE["cost_upper"],
                             "empty_body": STATE["empty_body"], "identity_bad": STATE["identity_bad"],
                             "blocked": STATE["blocked"]})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            body = json.loads(raw or b"{}")
        except Exception:
            body = {"_unparsed_head": raw[:300].decode("utf-8", "replace")}
        msgs = body.get("messages") or []
        with LOCK:
            over_calls = STATE["n"] >= MAX_CALLS
            over_cost = STATE["cost_upper"] >= MAX_CNY
        if over_calls or over_cost:
            with LOCK:
                STATE["blocked"] += 1
                STATE_log = dict(STATE)
            with open(USAGE_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": time.time(), "blocked": True, "n_messages": len(msgs),
                                    "reason": "max_calls" if over_calls else "max_cny",
                                    "state": STATE_log}, ensure_ascii=False) + "\n")
            self._json(402, {"error": {"message": "R475 budget guard: %s exceeded"
                                       % ("max_calls" if over_calls else "max_cny"),
                                       "type": "budget_guard"}})
            return

        t0 = time.time()
        req = urllib.request.Request(UPSTREAM, data=raw, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", "Bearer " + KEY)
        req.add_header("Accept", "application/json")
        status, payload, err = 0, b"", ""
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                status = r.status
                payload = r.read()
        except urllib.error.HTTPError as e:
            status = e.code
            payload = e.read()
            err = "HTTPError"
        except Exception as e:  # 网络层
            err = type(e).__name__ + ": " + str(e)[:200]
        ms = int((time.time() - t0) * 1000)

        try:
            usage = (json.loads(payload or b"{}") or {}).get("usage") or {}
        except Exception:
            usage = {}
        facts = choices_facts(payload)

        with LOCK:
            STATE["n"] += 1
            seq = STATE["n"]
            pt = int(usage.get("prompt_tokens") or 0)
            ctok = int(usage.get("completion_tokens") or 0)
            hit = int(usage.get("prompt_cache_hit_tokens") or 0)
            miss = int(usage.get("prompt_cache_miss_tokens") or 0)
            # R475: 恒等式**逐调用**判 (R474 是事后 29/29 复算, 违背当场不静默)
            identity_ok = bool(usage) and pt == hit + miss
            if usage and not identity_ok:
                STATE["identity_bad"] += 1
            if facts["empty_body"]:
                STATE["empty_body"] += 1
            cost = pt / 1e6 * PRICE_IN_PER_M + ctok / 1e6 * PRICE_OUT_PER_M
            STATE["cost_upper"] += cost
            STATE["prompt"] += pt
            STATE["completion"] += ctok
            STATE["hit"] += hit
            STATE["miss"] += miss
            cum = STATE["cost_upper"]
            with open(CALLS_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "seq": seq, "ts": round(t0, 4), "path": self.path, "model": body.get("model"),
                    "stream": bool(body.get("stream")), "n_messages": len(msgs),
                    "prompt_tokens_est": est_tokens_from_messages(msgs),
                    "sampling": sampling_of(body),
                    "messages": msgs,
                }, ensure_ascii=False) + "\n")
            with open(USAGE_PATH, "a", encoding="utf-8") as f:
                row = {
                    "seq": seq, "ts": round(t0, 4), "ms": ms, "status": status, "err": err,
                    "usage": usage, "prompt_tokens": pt, "completion_tokens": ctok,
                    "cache_hit_tokens": hit, "cache_miss_tokens": miss,
                    "identity_ok": identity_ok,
                    "cost_cny_upper": round(cost, 8), "cum_cost_cny_upper": round(cum, 8),
                }
                row.update(facts)
                if status != 200:
                    row["body_head"] = payload[:300].decode("utf-8", "replace")
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        if status and payload:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self._json(502, {"error": {"message": "relay upstream failure: " + err,
                                       "type": "relay_upstream"}})


if __name__ == "__main__":
    if not KEY:
        print("[致命] R475_UPSTREAM_KEY 未设置 ⇒ 拒绝启动 (不以 dummy key 打真端点)", flush=True)
        sys.exit(9)
    os.makedirs(OUTDIR, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("[relay-r475] :%d → %s  cap calls=%d cny=%.4f tag=%s" % (PORT, UPSTREAM, MAX_CALLS, MAX_CNY, TAG),
          flush=True)
    srv.serve_forever()
