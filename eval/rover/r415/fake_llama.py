#!/usr/bin/env python3
"""R415 假本地后端 — 模拟 llama-server 的最小 HTTP 面。

存在理由: 「门入参 = 用户本轮原文」必须在**真链 + 真端口 + 真 DI 装配**下被钉死, 而判定器不能是模型
(模型不可复现 ⇒ 判据只在单次读数下成立)。故用**确定性规则**替换模型:
用户原文含「谢谢」⇒ S(跳过), 否则 P(走远端)。

外部真值: 每个请求体逐条落盘 (R415_LOG); 判据只认这里, 被测量代码自报的遥测只作交叉核对
(R408 教训: 自算错而自洽最隐蔽)。

用法: R415_LOG=x.jsonl python3 fake_llama.py --port N [--model path]
"""
import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = os.environ.get("R415_LOG", "llamareq.jsonl")
_lock = threading.Lock()
# 假 BOS/EOS: 刻意不用尖括号形态, 避免源码写入期被 tokenizer 形态替换 (R413 铁律)
BOS = "\u00abr415_bos\u00bb"
EOS = "\u00abr415_eos\u00bb"
UM, UE = "[[user]]", "[[/user]]"
AM, AE = "[[assistant]]", "[[/assistant]]"


def _rec(obj):
    with _lock:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _text(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return ""


def render(messages):
    out = []
    for m in messages or []:
        r = m.get("role", "user")
        out.append((UM if r == "user" else AM) + _text(m.get("content")) + (UE if r == "user" else AE) + "\n")
    out.append(AM)
    return "".join(out)


def extract_user(prompt):
    """取「待判定的用户原文」。必须锚定【用户消息】段: 判别提示词自带的 few-shot 示例里
    就含「收到，谢谢。」, 若按全文匹配示例, 三轮都会判成 S (第一版即栽在这里)。"""
    txt = prompt or ""
    k = txt.rfind("【用户消息】")
    if k >= 0:
        seg = txt[k + len("【用户消息】"):]
        seg = seg.split("答案:")[0]
        return seg.strip()
    i = txt.rfind(UM)
    if i >= 0:
        j = txt.find(UE, i)
        if j > i:
            return txt[i + len(UM):j]
    return ""


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _read_raw(self):
        """HttpClient 可能以 chunked 发送 (无 Content-Length) ⇒ 必须显式解块, 否则请求体读成空。"""
        te = (self.headers.get("Transfer-Encoding") or "").lower()
        if "chunked" in te:
            out = b""
            while True:
                line = self.rfile.readline().strip()
                if not line:
                    break
                try:
                    n = int(line.split(b";")[0], 16)
                except ValueError:
                    break
                if n == 0:
                    self.rfile.readline()
                    break
                out += self.rfile.read(n)
                self.rfile.readline()
            return out
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _body(self):
        raw = self._read_raw()
        try:
            return json.loads(raw.decode("utf-8") or "{}"), raw.decode("utf-8", "replace")
        except Exception:
            return {}, raw.decode("utf-8", "replace")

    def do_GET(self):
        p = self.path.split("?")[0]
        _rec({"t": "GET", "path": p})
        if p.startswith("/health"):
            self._send({"status": "ok"})
        elif p.startswith("/props"):
            self._send({"bos_token": BOS, "eos_token": EOS,
                        "chat_template": "{# r415 fake jinja #}", "model_path": ARGS.model})
        elif p.startswith("/slots"):
            self._send([])
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self):
        b, raw = self._body()
        p = self.path.split("?")[0]
        if p.endswith("/apply-template"):
            msgs = b.get("messages") or b.get("turns") or []
            _rec({"t": "apply-template", "keys": sorted(b.keys()), "raw": raw[:2000],
                  "messages": msgs, "rendered": render(msgs)})
            self._send({"prompt": render(msgs)})
        elif p.endswith("/tokenize"):
            c = _text(b.get("content"))
            _rec({"t": "tokenize", "keys": sorted(b.keys()), "content": c[:400]})
            n = max(1, min(64, len(c)))
            self._send({"tokens": list(range(1, n + 1))})
        elif p.endswith("/completion"):
            prompt = b.get("prompt") or ""
            user = extract_user(prompt)
            content = "S" if "\u8c22\u8c22" in user else "P"
            _rec({"t": "completion", "keys": sorted(b.keys()), "raw": raw[:2000],
                  "prompt_len": len(prompt), "prompt": prompt[:4000],
                  "user": user, "verdict": content, "cache_prompt": b.get("cache_prompt")})
            self._send({"content": content, "tokens": [11, 12, 13], "tokens_predicted": 3,
                        "tokens_evaluated": max(1, len(prompt)), "stop": True,
                        "timings": {"prompt_n": max(1, len(prompt)), "cache_n": 0,
                                    "prompt_ms": 1.0, "predicted_ms": 1.0}})
        elif p.endswith("/v1/embeddings"):
            inp = b.get("input")
            k = len(inp) if isinstance(inp, list) else 1
            _rec({"t": "embeddings", "keys": sorted(b.keys()), "n": k})
            self._send({"data": [{"embedding": [0.01] * 8, "index": i} for i in range(k)],
                        "model": "r415-fake-embed"})
        else:
            _rec({"t": "post-unknown", "path": p, "keys": sorted(b.keys()), "raw": raw[:1200]})
            self._send({"error": "not found"}, 404)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--model", default="")
    ARGS = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", ARGS.port), H)
    print(f"[fake-llama] listening 127.0.0.1:{ARGS.port} log={LOG}", flush=True)
    srv.serve_forever()
