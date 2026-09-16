#!/usr/bin/env python3
"""codex 对照桩 — 记录 codex CLI 发出的**全量请求体**（含 tools 数组、system、参数）。

用途: 对照实验的"外部接口面"。codex 0.154.0 支持自定义 model_provider(base_url+env_key),
本桩按 OpenAI 兼容形状应答, 使 codex 能跑完一轮并把真实请求落盘。
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OUT = os.environ.get("CX_STUB_DIR", "/tmp/cxprobe")
N = {"n": 0}
LOCK = threading.Lock()
REPLY = os.environ.get("CX_STUB_REPLY", "桩应答: 收到。")


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _log(self, obj):
        with LOCK:
            N["n"] += 1
            p = os.path.join(OUT, f"req-{N['n']:03d}.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=1)
            print(f"[stub] req {N['n']} -> {p}", flush=True)

    def do_GET(self):
        body = json.dumps({"object": "list", "data": [{"id": "gpt-5-codex", "object": "model"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode("utf-8", "replace")
        try:
            obj = json.loads(raw)
        except Exception:
            obj = {"_raw": raw[:20000]}
        self._log({"path": self.path, "headers": dict(self.headers), "body": obj})
        # OpenAI 兼容的 chat.completions 应答（无 tool_calls ⇒ codex 立即收尾）
        resp = {
            "id": "chatcmpl-stub",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-5-codex",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": REPLY}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
        }
        b = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 48500
    os.makedirs(OUT, exist_ok=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
