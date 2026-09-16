#!/usr/bin/env python3
"""R454-demo 适配器 — 把两侧（codex 的 /v1/responses 与我方的 /v1/chat/completions）
统一转到**同一个真实模型**，并把双方请求体/应答全量落盘（Authorization 永不落盘）。

输出: <OUT>/side-{codex,agent}-NNN.json  (request+response 成对)
"""
import json
import os
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OUT = os.environ.get("DEMO_OUT", "/tmp/cxprobe/demo")
UPSTREAM = os.environ.get("DEMO_UPSTREAM", "https://api.deepseek.com/v1/chat/completions")
KEY = os.environ.get("AGENTFRAMEWORK_KEYS_DEEPSEEK", "")
MAP_MODEL = {"deepseek-flash": "deepseek-chat", "glm-5.3-flash": "deepseek-chat", "gpt-6": "deepseek-chat",
             "gpt-5-codex": "deepseek-chat"}
N = {"codex": 0, "agent": 0}
LOCK = threading.Lock()


def upstream_chat(messages, model, temperature=None, max_tokens=None):
    body = {"model": MAP_MODEL.get(model, model), "messages": messages, "stream": False}
    if temperature is not None:
        body["temperature"] = temperature
    if max_tokens:
        body["max_tokens"] = max_tokens
    req = urllib.request.Request(UPSTREAM, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return body, json.loads(r.read().decode("utf-8"))


def sse(ev, obj):
    return f"event: {ev}\ndata: {json.dumps(obj, ensure_ascii=False)}\n\n".encode()


def resp_items_to_messages(instructions, items):
    """codex: Responses 请求 → chat 请求（developer/user 消息按序拼接）。"""
    msgs = []
    if instructions:
        msgs.append({"role": "system", "content": instructions})
    for it in items or []:
        if it.get("type") == "message":
            c = it.get("content")
            if isinstance(c, list):
                txt = "\n".join(p.get("text", "") for p in c if isinstance(p, dict))
            else:
                txt = str(c)
            role = it.get("role") or "user"
            msgs.append({"role": "assistant" if role == "assistant" else ("system" if role == "developer" else "user"),
                         "content": txt})
        elif it.get("type") == "function_call_output":
            msgs.append({"role": "user", "content": f"[tool_output] {it.get('output')}"})
    return msgs


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _dump(self, side, req_body, resp_body, extra=None):
        with LOCK:
            N[side] += 1
            p = os.path.join(OUT, f"side-{side}-{N[side]:03d}.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"side": side, "request": req_body, "response": resp_body, "extra": extra or {}},
                          f, ensure_ascii=False, indent=1)
            print(f"[adapter] {side} #{N[side]} -> {p} (upstream_model={resp_body.get('model') if isinstance(resp_body, dict) else '?'})", flush=True)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n).decode("utf-8", "replace"))
        is_resp = self.path.rstrip("/").endswith("responses")
        side = "codex" if is_resp else "agent"
        if is_resp:
            msgs = resp_items_to_messages(body.get("instructions"), body.get("input"))
            tools_n = len(body.get("tools") or [])
            up_body, up_resp = upstream_chat(msgs, body.get("model", "deepseek-chat"))
            text = ""
            try:
                text = up_resp["choices"][0]["message"].get("content") or ""
            except Exception:
                pass
            self._dump(side, {"path": self.path, "instructions_chars": len(body.get("instructions") or ""),
                              "tools_n": tools_n, "input_items": len(body.get("input") or []),
                              "upstream_request": up_body},
                       {"model": up_resp.get("model"), "text": text, "usage": up_resp.get("usage")},
                       extra={"note": "codex tools 未透传（桩侧降级为纯文本对照）"})
            item = {"id": "msg_demo", "type": "message", "status": "completed", "role": "assistant",
                    "content": [{"type": "output_text", "text": text, "annotations": []}]}
            payload = b"".join(sse(e, o) for e, o in [
                ("response.created", {"type": "response.created", "response": {"id": "resp_demo", "status": "in_progress", "output": []}}),
                ("response.output_item.added", {"type": "response.output_item.added", "output_index": 0, "item": {"id": "msg_demo", "type": "message", "status": "in_progress", "role": "assistant", "content": []}}),
                ("response.output_text.delta", {"type": "response.output_text.delta", "item_id": "msg_demo", "output_index": 0, "content_index": 0, "delta": text}),
                ("response.output_item.done", {"type": "response.output_item.done", "output_index": 0, "item": item}),
                ("response.completed", {"type": "response.completed", "response": {"id": "resp_demo", "status": "completed", "output": [item],
                                                                                   "usage": up_resp.get("usage") or {}}}),
            ])
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        # 我方: chat 透传（仅改写模型名）
        up_body, up_resp = upstream_chat(body.get("messages") or [], body.get("model", "deepseek-chat"),
                                         body.get("temperature"), body.get("max_tokens"))
        self._dump(side, {"path": self.path, "n_messages": len(body.get("messages") or []),
                          "upstream_request": up_body},
                   {"model": up_resp.get("model"), "text": (up_resp.get("choices") or [{}])[0].get("message", {}).get("content"),
                    "usage": up_resp.get("usage")})
        b = json.dumps(up_resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 48600
    os.makedirs(OUT, exist_ok=True)
    print(f"[adapter] 127.0.0.1:{port} out={OUT} upstream={UPSTREAM} key={'SET' if KEY else 'MISSING'}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
