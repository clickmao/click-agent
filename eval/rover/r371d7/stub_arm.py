#!/usr/bin/env python3
"""R371-D7/D1 验收桩 — 确定性构造 半行截断 / 空正文 / 完整正文 三种远端应答, **逐请求落盘**(外部真值).

用法: python3 -u stub_arm.py <port> <out.jsonl> <mode>
  ok           : 每次返回完整正文(负控: 不得触发任何恢复)
  truncate     : 奇数次返回**半行截断**正文, 偶数次返回**重打断点前缀**的续写(测 MergeContinuation 去重)
  empty        : 奇数次 content="" 且 reasoning 非空(推理吃满预算), 偶数次返回完整正文
  empty_always : 每次都 content="" 且 reasoning 非空(测"仍空 => 可见降级 + Success=false")

落盘每行含: seq/n_messages/nudge(请求里出现的恢复提示)/token 估算/messages 原文
口径: token = 字符数/2 的**估算**(非真 tokenizer); 仅同口径比较用。
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
OUT = sys.argv[2]
MODE = sys.argv[3] if len(sys.argv) > 3 else "ok"

HEAD = ("以下是求和函数的实现(前半):\n\ndef total(nums):\n    acc = 0\n    for n in nums:\n"
        "        acc += n\n    start_len: int =")
TAIL = "start_len: int = 12\n    return acc\n\n（说明：返回列表元素之和，空列表返回 0。）"
FULL = "求和函数实现完成：total(nums) 对列表元素求和，空列表返回 0。"
REASONING = "让我先分析这个需求。" * 40
NUDGE_TRUNC = "只输出断点之后的剩余内容"
NUDGE_NOREASON = "不要输出思考/推理过程"

LOCK = threading.Lock()
COUNT = {"n": 0}


def est(msgs):
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


def pick(seq):
    """返回 (content, reasoning, finish_reason, completion_tokens)"""
    odd = seq % 2 == 1
    if MODE == "ok":
        return FULL, None, "stop", max(1, len(FULL) // 2)
    if MODE == "truncate":
        return (HEAD, None, "length", 8192) if odd else (TAIL, None, "stop", 64)
    if MODE == "empty":
        return ("", REASONING, "length", 8192) if odd else (FULL, None, "stop", 48)
    if MODE == "empty_always":
        return "", REASONING, "length", 8192
    raise SystemExit("unknown mode: " + MODE)


def flatten_text(msgs):
    out = []
    for m in msgs:
        ct = m.get("content")
        if isinstance(ct, str):
            out.append(ct)
        elif isinstance(ct, list):
            for part in ct:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    out.append(part["text"])
    return "\n".join(out)


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
            self._json(200, {"ok": True})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            body = json.loads(raw or b"{}")
        except Exception:
            body = {}
        msgs = body.get("messages") or []
        flat = flatten_text(msgs)
        pt = est(msgs)
        with LOCK:
            COUNT["n"] += 1
            seq = COUNT["n"]
        content, reasoning, finish, ct = pick(seq)
        with LOCK:
            with open(OUT, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "seq": seq, "path": self.path, "model": body.get("model"),
                    "stream": bool(body.get("stream")), "n_messages": len(msgs),
                    "mode": MODE, "finish_reason": finish,
                    "nudge_trunc": NUDGE_TRUNC in flat, "nudge_noreason": NUDGE_NOREASON in flat,
                    "prompt_tokens_est": pt, "completion_tokens_est": ct,
                    "resp_content": content, "resp_content_len": len(content),
                    "resp_reasoning_len": len(reasoning or ""),
                    "messages": msgs,
                }, ensure_ascii=False) + "\n")

        model = body.get("model") or "stub-model"
        usage = {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            delta = {"role": "assistant", "content": content}
            if reasoning:
                delta["reasoning_content"] = reasoning
            first = {"id": f"stub-{seq}", "object": "chat.completion.chunk", "model": model,
                     "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
            self.wfile.write(f"data: {json.dumps(first, ensure_ascii=False)}\n\n".encode())
            last = {"id": f"stub-{seq}", "object": "chat.completion.chunk", "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": finish}], "usage": usage}
            self.wfile.write(f"data: {json.dumps(last, ensure_ascii=False)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            return

        msg = {"role": "assistant", "content": content}
        if reasoning:
            msg["reasoning_content"] = reasoning
        self._json(200, {
            "id": f"stub-{seq}", "object": "chat.completion", "created": 0, "model": model,
            "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
            "usage": usage,
        })


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    sys.stderr.write(f"stub_arm: 127.0.0.1:{PORT} mode={MODE} -> {OUT}\n")
    sys.stderr.flush()
    srv.serve_forever()
