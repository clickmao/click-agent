#!/usr/bin/env python3
"""codex 对照桩 v2 — 支持 Responses API（codex 0.154 仅支持 responses wire_api）。

记录 codex 发出的**全量请求体**（含 tools 数组 / instructions / input / 采样参数），
并以最小 SSE 事件流应答，使 codex 能跑完一轮。
"""
import gzip
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OUT = os.environ.get("CX_STUB_DIR", "/tmp/cxprobe")
N = {"n": 0}
LOCK = threading.Lock()
REPLY = os.environ.get("CX_STUB_REPLY", "桩应答: 收到。")


def sse(ev, obj):
    return f"event: {ev}\ndata: {json.dumps(obj, ensure_ascii=False)}\n\n".encode()


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _log(self, path, headers, body):
        with LOCK:
            N["n"] += 1
            p = os.path.join(OUT, f"req-{N['n']:03d}.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"path": path, "headers": headers, "body": body}, f, ensure_ascii=False, indent=1)
            print(f"[stub] req {N['n']} {path} -> {p}", flush=True)

    def do_GET(self):
        b = json.dumps({"object": "list", "data": [{"id": "gpt-5-codex", "object": "model"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        if (self.headers.get("Content-Encoding") or "").lower() == "gzip":
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
        txt = raw.decode("utf-8", "replace")
        try:
            body = json.loads(txt)
        except Exception:
            body = {"_raw": txt[:40000]}
        self._log(self.path, dict(self.headers), body)

        if self.path.rstrip("/").endswith("responses"):
            item = {"id": "msg_stub1", "type": "message", "status": "completed", "role": "assistant",
                    "content": [{"type": "output_text", "text": REPLY, "annotations": []}]}
            evs = [
                ("response.created", {"type": "response.created", "response": {"id": "resp_stub1", "object": "response", "status": "in_progress", "output": []}}),
                ("response.output_item.added", {"type": "response.output_item.added", "output_index": 0, "item": {"id": "msg_stub1", "type": "message", "status": "in_progress", "role": "assistant", "content": []}}),
                ("response.output_text.delta", {"type": "response.output_text.delta", "item_id": "msg_stub1", "output_index": 0, "content_index": 0, "delta": REPLY}),
                ("response.output_item.done", {"type": "response.output_item.done", "output_index": 0, "item": item}),
                ("response.completed", {"type": "response.completed", "response": {"id": "resp_stub1", "object": "response", "status": "completed", "output": [item],
                                                                                   "usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}}}),
            ]
            payload = b"".join(sse(e, o) for e, o in evs)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        resp = {"id": "chatcmpl-stub", "object": "chat.completion", "created": 0, "model": "gpt-5-codex",
                "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": REPLY}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}}
        b = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):  # noqa: D102
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 48500
    os.makedirs(OUT, exist_ok=True)
    print(f"[stub] listening 127.0.0.1:{port} dir={OUT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
