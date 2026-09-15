#!/usr/bin/env python3
"""R455 — **透传工具面** 的对照适配器：codex(/v1/responses, 含 tools) ⇄ chat(DeepSeek)。

与 R454 的 demo 适配器差别：**不再丢弃 codex 的 tools**，并把上游 chat 的 `tool_calls`
翻回 Responses 的 `function_call` 输出项 ⇒ codex 能真正执行 shell/写文件（公平能力对照）。
Authorization 永不落盘。
"""
import json
import os
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OUT = os.environ.get("DEMO_OUT", "/tmp/cxprobe/r455")


def resp_usage(u):
    u = u or {}
    return {"input_tokens": u.get("prompt_tokens", 0), "output_tokens": u.get("completion_tokens", 0),
            "total_tokens": u.get("total_tokens", 0),
            "input_tokens_details": {"cached_tokens": u.get("prompt_cache_hit_tokens", 0)},
            "output_tokens_details": {"reasoning_tokens": 0}}
UPSTREAM = os.environ.get("DEMO_UPSTREAM", "https://api.deepseek.com/v1/chat/completions")
KEY = os.environ.get("AGENTFRAMEWORK_KEYS_DEEPSEEK", "")
MAP_MODEL = {"deepseek-flash": "deepseek-chat", "glm-5.3-flash": "deepseek-chat", "gpt-6": "deepseek-chat",
             "gpt-5-codex": "deepseek-chat"}
N = {"codex": 0, "agent": 0}
LOCK = threading.Lock()
CONV = {}  # thread_key -> chat messages 累积（上游 chat 无状态）


def upstream_chat(messages, model, tools=None, max_tokens=None):
    body = {"model": MAP_MODEL.get(model, model), "messages": messages, "stream": False}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    if max_tokens:
        body["max_tokens"] = max_tokens
    req = urllib.request.Request(UPSTREAM, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return body, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("[upstream 4xx] ", e.code, e.read().decode("utf-8", "replace")[:800], flush=True)
        raise


def to_chat_tools(tools):
    # R456: 兼容两种声明形态 —— Responses 风({type,name,parameters}) 与 chat 风({type,function:{...}})。
    #   旧版只认 Responses 风 ⇒ 我方(chat 风)的 tools 会被静默丢弃 (器具缺陷, 本轮实测捕获)。
    out = []
    for t in tools or []:
        if t.get("type") == "function" and t.get("function"):
            fn = t["function"] or {}
            out.append({"type": "function", "function": {"name": fn.get("name"), "description": fn.get("description") or "",
                                                         "parameters": fn.get("parameters") or {"type": "object", "properties": {}}}})
        elif t.get("type") == "function" and t.get("name"):
            out.append({"type": "function", "function": {"name": t["name"], "description": t.get("description") or "",
                                                         "parameters": t.get("parameters") or {"type": "object", "properties": {}}}})
    return out


def items_to_messages(instructions, items):
    msgs = []
    if instructions:
        msgs.append({"role": "system", "content": instructions})
    for it in items or []:
        t = it.get("type")
        if t == "message":
            c = it.get("content")
            txt = "\n".join(p.get("text", "") for p in c if isinstance(p, dict)) if isinstance(c, list) else str(c)
            role = it.get("role") or "user"
            msgs.append({"role": "assistant" if role == "assistant" else ("system" if role == "developer" else "user"),
                         "content": txt})
        elif t == "function_call":
            msgs.append({"role": "assistant", "content": "",
                         "tool_calls": [{"id": it.get("call_id") or it.get("id"), "type": "function",
                                         "function": {"name": it.get("name"), "arguments": it.get("arguments") or "{}"}}]})
        elif t == "function_call_output":
            msgs.append({"role": "tool", "tool_call_id": it.get("call_id"), "content": str(it.get("output"))[:6000]})
    return msgs


def sse(ev, obj):
    return f"event: {ev}\ndata: {json.dumps(obj, ensure_ascii=False)}\n\n".encode()



def _sha8(txt):
    import hashlib
    return hashlib.sha256((txt or '').encode('utf-8', 'replace')).hexdigest()[:8]


def _tail(msgs, n=4, head=200):
    out = []
    for m in (msgs or [])[-n:]:
        c = m.get('content')
        if not isinstance(c, str):
            c = json.dumps(c, ensure_ascii=False)[:head] if c is not None else ''
        out.append({'role': m.get('role'), 'len': len(c), 'head': c[:head], 'tool_calls': len(m.get('tool_calls') or []), 'tool_call_id': m.get('tool_call_id')})
    return out

class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _dump(self, side, req, resp, extra=None, full=None):
        with LOCK:
            N[side] += 1
            p = os.path.join(OUT, f"side-{side}-{N[side]:03d}.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"side": side, "request": req, "response": resp, "extra": extra or {}}, f, ensure_ascii=False, indent=1)
            # R460 器具: 全量实发消息落盘 (ADAPTER_DUMP_FULL=1) ⇒ 逐块归因, 禁重建/禁估算。
            if os.environ.get("ADAPTER_DUMP_FULL") == "1" and full is not None:
                slim = []
                for m in full:
                    c = m.get("content")
                    if not isinstance(c, str):
                        c = "" if c is None else json.dumps(c, ensure_ascii=False)
                    slim.append({"role": m.get("role"), "content": c[:12000],
                                 "tool_calls": len(m.get("tool_calls") or []), "tool_call_id": m.get("tool_call_id")})
                fp = os.path.join(OUT, f"full-{side}-{N[side]:03d}.json")
                with open(fp, "w", encoding="utf-8") as f2:
                    json.dump(slim, f2, ensure_ascii=False)
                print(f"[adapter] FULL {side} #{N[side]} -> {fp}", flush=True)
            print(f"[adapter] {side} #{N[side]} -> {p}", flush=True)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n).decode("utf-8", "replace"))
        is_resp = self.path.rstrip("/").endswith("responses")
        side = "codex" if is_resp else "agent"
        if is_resp:
            msgs = items_to_messages(body.get("instructions"), body.get("input"))
            tl = to_chat_tools(body.get("tools"))
            up_body, up = upstream_chat(msgs, body.get("model", "deepseek-chat"), tl)
            ch = (up.get("choices") or [{}])[0]
            msg = ch.get("message") or {}
            out_items, evs = [], []
            if msg.get("tool_calls"):
                for i, tc in enumerate(msg["tool_calls"]):
                    cid = tc.get("id") or f"call_{i}"
                    fn = tc.get("function") or {}
                    it = {"id": f"fc_{i}", "type": "function_call", "status": "completed", "call_id": cid,
                          "name": fn.get("name"), "arguments": fn.get("arguments") or "{}"}
                    evs += [("response.output_item.added", {"type": "response.output_item.added", "output_index": i,
                                                            "item": {"id": f"fc_{i}", "type": "function_call", "status": "in_progress",
                                                                     "call_id": cid, "name": fn.get("name"), "arguments": ""}}),
                            ("response.function_call_arguments.delta", {"type": "response.function_call_arguments.delta",
                                                                        "item_id": f"fc_{i}", "output_index": i,
                                                                        "delta": fn.get("arguments") or "{}"}),
                            ("response.output_item.done", {"type": "response.output_item.done", "output_index": i, "item": it})]
                    out_items.append(it)
                _txt = ""
            else:
                _txt = msg.get("content") or ""
                it = {"id": "msg_r455", "type": "message", "status": "completed", "role": "assistant",
                      "content": [{"type": "output_text", "text": _txt, "annotations": []}]}
                evs += [("response.output_item.added", {"type": "response.output_item.added", "output_index": 0,
                                                        "item": {"id": "msg_r455", "type": "message", "status": "in_progress",
                                                                 "role": "assistant", "content": []}}),
                        ("response.output_text.delta", {"type": "response.output_text.delta", "item_id": "msg_r455",
                                                        "output_index": 0, "content_index": 0, "delta": _txt}),
                        ("response.output_item.done", {"type": "response.output_item.done", "output_index": 0, "item": it})]
                out_items.append(it)
            self._dump(side, {"instructions_chars": len(body.get("instructions") or ""), "tools_n": len(body.get("tools") or []),
                              "passed_tools_n": len(tl), "input_items": len(body.get("input") or []),
                              "upstream_request": {"model": up_body.get("model"), "n_messages": len(up_body["messages"]),
                                                   "tools": [t["function"]["name"] for t in up_body.get("tools") or []]}},
                       {"tool_calls": [{"name": (tc.get("function") or {}).get("name"), "args": (tc.get("function") or {}).get("arguments")} for tc in (msg.get("tool_calls") or [])],
                        "text": _txt, "usage": up.get("usage")}, full=up_body.get("messages"))
            payload = b"".join(sse(e, o) for e, o in [
                ("response.created", {"type": "response.created", "response": {"id": "resp_r455", "status": "in_progress", "output": []}})] + evs + [
                ("response.completed", {"type": "response.completed", "response": {"id": "resp_r455", "status": "completed",
                                                                                  "output": out_items, "usage": resp_usage(up.get("usage"))}})])
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        # 我方 chat 透传（含 tools，若有）
        up_body, up = upstream_chat(body.get("messages") or [], body.get("model", "deepseek-chat"),
                                    to_chat_tools(body.get("tools")), body.get("max_tokens"))
        self._dump(side, {"n_messages": len(body.get("messages") or []), "tools_n": len(to_chat_tools(body.get("tools"))),
                          "upstream_request": {"model": up_body.get("model"), "n_messages": len(up_body["messages"]),
                                            "prompt_sha8": _sha8(json.dumps(up_body.get("messages") or [], ensure_ascii=False, sort_keys=True)),
                                            "tail_messages": _tail(up_body.get("messages"))}},
                   {"text": ((up.get("choices") or [{}])[0].get("message") or {}).get("content"), "usage": up.get("usage"),
                    "tool_calls": [{"name": (tc.get("function") or {}).get("name"), "args": (tc.get("function") or {}).get("arguments")} for tc in ((up.get("choices") or [{}])[0].get("message") or {}).get("tool_calls") or []],
                    "finish_reason": (up.get("choices") or [{}])[0].get("finish_reason")}, full=up_body.get("messages"))
        b = json.dumps(up).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 48610
    os.makedirs(OUT, exist_ok=True)
    print(f"[adapter] 127.0.0.1:{port} out={OUT} key={'SET' if KEY else 'MISSING'}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
