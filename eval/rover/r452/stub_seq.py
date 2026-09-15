#!/usr/bin/env python3
"""R452 远端桩（带回复序列）— OpenAI 兼容 /v1/chat/completions, **逐请求落盘**。

与 r430/stub_openai.py 的差别: 回复不再是常量, 而是按**调用序号**从 reply-seq.json 取,
以便让产品的门判 prev（`_lastReplyBySession`）吃到**该会话真实的上一轮回答** —— 这是
「产品原生跑真实语料」的保真关键（R451 教训: 重建器具必先有实发文本锚, 此处改为零重建）。

对齐校验: 每行落盘 `seq`/`last_user` ⇒ 分析器逐轮断言 `last_user == turns[seq-1]`,
不符即记 `prev_chain_drift`（诚实口径, 不静默）。

用法: python3 -u stub_seq.py <port> <out.jsonl> <reply-seq.json> <task.json> [默认回复]

reply-seq.json[i] = **turn i 的应答**（= 语料里 turn i+1 的 prev_reply）⇒ 产品对 turn i 的
回答即成为 turn i+1 门判所见 prev，链式保真。
"""
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
OUT = sys.argv[2]
REPLIES = json.load(open(sys.argv[3], encoding="utf-8"))
_TASK = json.load(open(sys.argv[4], encoding="utf-8")) if len(sys.argv) > 4 else {}
TURNS = _TASK.get("turns") or []
DEFAULT = sys.argv[5] if len(sys.argv) > 5 else "桩应答: 收到, 已完成该步。"  # 与 R450 臂同字面, 保对照可比
PTR = {"j": 0}
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


def last_user(msgs):
    for m in reversed(msgs or []):
        if m.get("role") == "user":
            ct = m.get("content")
            if isinstance(ct, str):
                return ct
            if isinstance(ct, list):
                return "".join(p.get("text", "") for p in ct if isinstance(p, dict))
    return ""


def match_turn(lu):
    """轮感知对齐: 产品会在 user 消息后追加「[本轮参考上下文]…」⇒ 只能前缀匹配。

    被吞并轮(产品计划复用, 0 远端调用)会跳过 ⇒ 指针只能前进, 不能按下标硬取。
    返回 (turn_index 或 None, gap)。
    """
    j = PTR["j"]
    while j < len(TURNS):
        probe = TURNS[j][:64]
        if probe and lu.startswith(probe):
            gap = j - PTR["j"]
            PTR["j"] = j + 1
            return j, gap
        j += 1
    return None, None


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
        self._json(200, {"ok": True}) if self.path.startswith("/health") else self._json(404, {"error": "nf"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            body = json.loads(raw or b"{}")
        except Exception:
            body = {}
        msgs = body.get("messages") or []
        lu = last_user(msgs)
        with LOCK:
            COUNT["n"] += 1
            seq = COUNT["n"]
            j, gap = match_turn(lu)
            if j is not None:
                reply = REPLIES[j] if j < len(REPLIES) else DEFAULT
            else:
                reply = DEFAULT
            pt = est_tokens_from_messages(msgs)
            ct = max(1, len(reply) // 2)
            with open(OUT, "a", encoding="utf-8") as f:
                f.write(json.dumps({"seq": seq, "path": self.path, "model": body.get("model"),
                                    "ts": time.time(), "stream": bool(body.get("stream")),
                                    "n_messages": len(msgs), "last_user": lu,
                                    "match_turn": (j + 1) if j is not None else None, "align_gap": gap,
                                    "used": "turn" if j is not None else "default",
                                    "reply_len": len(reply), "in_seq": seq <= len(REPLIES),
                                    "prompt_tokens_est": pt, "completion_tokens_est": ct},
                                   ensure_ascii=False) + "\n")
        model = body.get("model") or "stub-model"
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            first = {"id": f"stub-{seq}", "object": "chat.completion.chunk", "model": model,
                     "choices": [{"index": 0, "delta": {"role": "assistant", "content": reply},
                                  "finish_reason": None}]}
            self.wfile.write(f"data: {json.dumps(first, ensure_ascii=False)}\n\n".encode())
            last = {"id": f"stub-{seq}", "object": "chat.completion.chunk", "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}}
            self.wfile.write(f"data: {json.dumps(last, ensure_ascii=False)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            return
        self._json(200, {"id": f"stub-{seq}", "object": "chat.completion", "created": 0, "model": model,
                         "choices": [{"index": 0, "message": {"role": "assistant", "content": reply},
                                      "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}})


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    sys.stderr.write(f"stub_seq: 127.0.0.1:{PORT} → {OUT} (seq n={len(REPLIES)})\n")
    sys.stderr.flush()
    srv.serve_forever()
