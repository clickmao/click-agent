#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R509 前端任务事件真机探针 (TCP / JSON Lines, 契约见 FrontendApiContract.cs)。

流程: auth → chat.send (真链真模型) → 收齐事件+响应 → state.snapshot → 落一个 JSON:
  {"events":[{"event","payload"}...], "response":{...}, "snapshot":{...}, "asks":N, "secs":x}
用法: python3 probe_frontend_tasks.py --port 48675 --out /tmp/r509/e2e.json [--text "..."]
"""
from __future__ import annotations
import argparse, json, os, socket, sys, time

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--text", default="回答：1+1=? 只回一个数字。")
    ap.add_argument("--timeout", type=float, default=240.0)
    a = ap.parse_args()
    token = os.environ.get("AGENTFRAMEWORK_FRONTEND_TOKEN", "")
    sock = socket.create_connection(("127.0.0.1", a.port), timeout=30)
    sock.settimeout(a.timeout)
    buf = b""
    def send(o):
        sock.sendall((json.dumps(o, ensure_ascii=False) + "\n").encode("utf-8"))
    def readline():
        nonlocal buf
        while b"\n" not in buf:
            d = sock.recv(65536)
            if not d:
                return None
            buf += d
        line, buf = buf.split(b"\n", 1)
        return line.decode("utf-8", "replace")
    if token:
        send({"type": "auth", "token": token}); time.sleep(0.2)
    out = {"events": [], "asks": 0, "secs": None, "text": a.text}
    t0 = time.time()
    send({"v": 1, "type": "req", "req_id": "r1", "api": "chat.send", "payload": {"text": a.text}})
    while True:
        line = readline()
        if line is None:
            out["error"] = "connection_closed"; break
        try:
            m = json.loads(line)
        except Exception:
            continue
        if m.get("type") == "event":
            p = m.get("payload") if isinstance(m.get("payload"), dict) else {}
            out["events"].append({"event": m.get("event"), "payload": p})
            if p.get("ask_id"):
                out["asks"] += 1
                send({"v": 1, "type": "req", "req_id": "a1", "api": "ask.reply",
                      "payload": {"ask_id": p["ask_id"], "text": "是"}})
            continue
        if m.get("type") == "resp" and m.get("req_id") == "r1":
            out["response"] = {"ok": m.get("ok"), "payload": m.get("payload"), "error": m.get("error")}
            break
    out["secs"] = round(time.time() - t0, 2)
    # state.snapshot: 断线重连面 — tasks[] 必须存在
    try:
        send({"v": 1, "type": "req", "req_id": "s1", "api": "state.snapshot", "payload": {}})
        while True:
            line = readline()
            if line is None:
                out["snapshot"] = {"error": "closed"}; break
            m = json.loads(line)
            if m.get("type") == "resp" and m.get("req_id") == "s1":
                out["snapshot"] = {"ok": m.get("ok"), "payload": m.get("payload")}
                break
    except Exception as e:
        out["snapshot"] = {"error": str(e)}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    names = [e["event"] for e in out["events"]]
    print(f"PROBE secs={out['secs']} events={names} resp_ok={(out.get('response') or {}).get('ok')} asks={out['asks']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
