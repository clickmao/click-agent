#!/usr/bin/env python3
"""R474 真实转发中继 — 双证据 + 预算闸 (fail-closed)。

存在理由: R465–R467 的 KPI 分母来自**桩侧记账**(字符数/2 估算), R470–R472 说明真实供应商
usage 与桩估算**不同源**(命中/新算只有供应商知道) ⇒ 需要「请求体仍可外部捕获」且「读数是
供应商 usage」的器具。中继 = 本地端口(宿主以为它在跟桩说话) → 转发真端点 → 逐请求落盘。

两条证据:
  (a) 请求面: calls-<tag>.jsonl  — 宿主**实发** messages 全文 (可做前缀/字节分析, 与桩同口径)
  (b) 读数面: usage-<tag>.jsonl  — 供应商返回的 usage (prompt/completion/cache_hit/cache_miss)
预算闸 (预注册): 调用数上限 ∧ 成本上限(按 config/base/models.yaml:27,28 单价, 命中不折价=上界)
  越限 ⇒ 不再转发, 直接回 402 错误体 (fail-closed, 不静默超额)。

凭据: 上游 key 由 R474_UPSTREAM_KEY 传入 (中继不经手文件); 宿主侧只用 dummy key。
       任何日志都不写 Authorization 头, 也不写上游 key。
用法: python3 -u relay_real.py <port> <max_calls> <max_cny> <outdir> <tag> [upstream_url]
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
    "R474_UPSTREAM", "https://api.deepseek.com/v1/chat/completions")
KEY = os.environ.get("R474_UPSTREAM_KEY", "")
PRICE_IN_PER_M = 0.27      # config/base/models.yaml deepseek-flash（缓存命中未折价 ⇒ 成本上界）
PRICE_OUT_PER_M = 1.10

CALLS_PATH = os.path.join(OUTDIR, "calls-%s.jsonl" % TAG)
USAGE_PATH = os.path.join(OUTDIR, "usage-%s.jsonl" % TAG)
LOCK = threading.Lock()
STATE = {"n": 0, "cost_upper": 0.0, "blocked": 0, "prompt": 0, "completion": 0,
         "hit": 0, "miss": 0}


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
            self._json(200, {"ok": True, "calls": STATE["n"], "cost_upper": STATE["cost_upper"]})
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
            self._json(402, {"error": {"message": "R474 budget guard: %s exceeded"
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

        usage = {}
        try:
            usage = (json.loads(payload or b"{}") or {}).get("usage") or {}
        except Exception:
            pass

        with LOCK:
            STATE["n"] += 1
            seq = STATE["n"]
            pt = int(usage.get("prompt_tokens") or 0)
            ctok = int(usage.get("completion_tokens") or 0)
            hit = int(usage.get("prompt_cache_hit_tokens") or 0)
            miss = int(usage.get("prompt_cache_miss_tokens") or 0)
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
                    "messages": msgs,
                }, ensure_ascii=False) + "\n")
            with open(USAGE_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "seq": seq, "ts": round(t0, 4), "ms": ms, "status": status, "err": err,
                    "usage": usage, "prompt_tokens": pt, "completion_tokens": ctok,
                    "cache_hit_tokens": hit, "cache_miss_tokens": miss,
                    "cost_cny_upper": round(cost, 8), "cum_cost_cny_upper": round(cum, 8),
                }, ensure_ascii=False) + "\n")

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
        print("[致命] R474_UPSTREAM_KEY 未设置 ⇒ 拒绝启动 (不以 dummy key 打真端点)", flush=True)
        sys.exit(9)
    os.makedirs(OUTDIR, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("[relay] :%d → %s  cap calls=%d cny=%.4f tag=%s" % (PORT, UPSTREAM, MAX_CALLS, MAX_CNY, TAG),
          flush=True)
    srv.serve_forever()
