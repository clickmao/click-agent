#!/usr/bin/env python3
"""R413 远端桩 — OpenAI 兼容 /v1/chat/completions, **逐请求落盘**。

存在理由: 判据 C1/C2 的计数必须取**外部真值**(桩服务端), 而不是被测量代码自报的计数器 —
自算错而自洽是最隐蔽的失真形态 (见 docs/improvements.md R408 教训)。

用法: python3 -u stub_openai.py <port> <out.jsonl> [固定回复]
落盘每行: {"path","model","stream","n_messages","prompt_tokens_est","completion_tokens_est","messages"}
口径: token 估算 = 字符数/2 (显式标注为**估算**, 非真 tokenizer; 两臂同口径 ⇒ 比值有效)。
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
OUT = sys.argv[2]
REPLY = sys.argv[3] if len(sys.argv) > 3 else "桩应答: 收到, 已完成该步。"
LOCK = threading.Lock()
COUNT = {"n": 0}


def est_tokens_from_messages(msgs):
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

    def log_message(self, *a):  # 静音
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
            self._json(200, {"ok": True})
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
        pt = est_tokens_from_messages(msgs)
        ct = max(1, len(REPLY) // 2)
        with LOCK:
            COUNT["n"] += 1
            seq = COUNT["n"]
            with open(OUT, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "seq": seq, "path": self.path, "model": body.get("model"),
                    "ts": __import__("time").time(),  # R423: 到达时刻 ⇒ 与轮时间窗对账归属
                    "stream": bool(body.get("stream")), "n_messages": len(msgs),
                    "prompt_tokens_est": pt, "completion_tokens_est": ct,
                    "messages": msgs,
                }, ensure_ascii=False) + "\n")

        model = body.get("model") or "stub-model"
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            first = {"id": f"stub-{seq}", "object": "chat.completion.chunk", "model": model,
                     "choices": [{"index": 0, "delta": {"role": "assistant", "content": REPLY}, "finish_reason": None}]}
            self.wfile.write(f"data: {json.dumps(first, ensure_ascii=False)}\n\n".encode())
            last = {"id": f"stub-{seq}", "object": "chat.completion.chunk", "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}}
            self.wfile.write(f"data: {json.dumps(last, ensure_ascii=False)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            return

        self._json(200, {
            "id": f"stub-{seq}", "object": "chat.completion", "created": 0, "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": REPLY}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct},
        })


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    sys.stderr.write(f"stub_openai: 监听 127.0.0.1:{PORT} → {OUT}\n")
    sys.stderr.flush()
    srv.serve_forever()
