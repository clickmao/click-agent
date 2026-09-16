#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R486 确定性上游桩: 固定形状响应, 用于『空正文浪费重试』的可测化差分.

语言无关: 判据只依据「桩收到的请求条数」与「宿主遥测的 retry_skipped 布尔」.
用法: stub_upstream_r486.py <port> <mode: empty_toolcall|plain> <outdir> <tag> [cap]
"""
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
MODE = sys.argv[2]
OUTDIR = sys.argv[3]
TAG = sys.argv[4]
CAP = int(sys.argv[5]) if len(sys.argv) > 5 else 200
REQ = os.path.join(OUTDIR, "stub-requests-%s.jsonl" % TAG)
LOCK = threading.Lock()
N = [0]


def make_body(n):
    msg = {"role": "assistant", "content": ""}
    if MODE == "empty_toolcall":
        msg["tool_calls"] = [{
            "id": "call_r486_%d" % n,
            "type": "function",
            "function": {"name": "list_dir", "arguments": json.dumps({"path": "."})},
        }]
        finish = "tool_calls"
    else:
        msg["content"] = "R486 桩: 固定正文答复。"
        finish = "stop"
    return {
        "id": "chatcmpl-stub-%d" % n,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "stub-r486",
        "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
        "usage": {
            "prompt_tokens": 32, "completion_tokens": 8, "total_tokens": 40,
            "prompt_tokens_details": {"cached_tokens": 0},
            "completion_tokens_details": {"reasoning_tokens": 0},
        },
    }


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        return

    def _send(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        except OSError:
            pass

    def do_GET(self):
        self._send({"ok": True, "mode": MODE, "served": N[0]})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        with LOCK:
            N[0] += 1
            i = N[0]
            if i > CAP:
                self._send({"error": {"message": "stub cap reached"}}, 429)
                return
            try:
                keys = sorted(json.loads(raw or b"{}").keys())
            except Exception:
                keys = []
            with open(REQ, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "seq": i, "ts": round(time.time(), 4), "path": self.path,
                    "bytes": len(raw), "top_keys": keys,
                    "has_tools": b'"tools"' in raw,
                    "tool_choice_present": b'"tool_choice"' in raw,
                    "stream_true": b'"stream": true' in raw or b'"stream":true' in raw,
                    "has_role": b'"role"' in raw,
                }, ensure_ascii=False) + "\n")
        self._send(make_body(i))


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    sys.stderr.write("[stub] :%d mode=%s tag=%s\n" % (PORT, MODE, TAG))
    sys.stderr.flush()
    srv.serve_forever()
