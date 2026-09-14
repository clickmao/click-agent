#!/usr/bin/env python3
"""R371-D7/D1 驱动器 — 通过 frontend-api (JSON Lines / TCP) 驱动**真链**, 记录 reply/success/事件。

用法: python3 -u drive_d7.py <port> <task.json> [out.jsonl]
"""
import json
import os
import socket
import sys
import time

PORT = int(sys.argv[1])
TASK = json.load(open(sys.argv[2], encoding="utf-8"))
OUT = sys.argv[3] if len(sys.argv) > 3 else ""
sock = socket.create_connection(("127.0.0.1", PORT), timeout=30)
sock.settimeout(float(TASK.get("turn_timeout_s", 600)))
buf = b""
TOKEN = os.environ.get("AGENTFRAMEWORK_FRONTEND_TOKEN", "")
if TOKEN:
    sock.sendall((json.dumps({"type": "auth", "token": TOKEN}) + "\n").encode("utf-8"))
    time.sleep(0.2)
stats = {"turns": 0, "ok": 0, "events": 0, "asks": 0, "errors": []}
records = []


def send(obj):
    sock.sendall((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))


def readline():
    global buf
    while b"\n" not in buf:
        d = sock.recv(65536)
        if not d:
            return None
        buf += d
    line, buf = buf.split(b"\n", 1)
    return line.decode("utf-8", "replace")


for i, turn in enumerate(TASK["turns"]):
    rid = f"t{i + 1}"
    stats["turns"] += 1
    t0 = time.time()
    send({"v": 1, "type": "req", "req_id": rid, "api": "chat.send", "payload": {"text": turn}})
    rec = {"turn": i + 1, "text": turn, "reply": None, "ok": None, "success": None, "events": [], "secs": None}
    while True:
        line = readline()
        if line is None:
            rec["ok"] = False
            rec["error"] = "connection_closed"
            stats["errors"].append(f"{rid}:eof")
            break
        try:
            m = json.loads(line)
        except Exception:
            continue
        kind = m.get("type")
        if kind == "event":
            stats["events"] += 1
            p = m.get("payload") if isinstance(m.get("payload"), dict) else {}
            rec["events"].append({"event": m.get("event"), "keys": sorted(p.keys())[:6]})
            ask_id = p.get("ask_id") or p.get("askId")
            if ask_id:
                stats["asks"] += 1
                send({"v": 1, "type": "req", "req_id": f"a{i + 1}",
                      "api": "ask.reply", "payload": {"ask_id": ask_id, "text": TASK.get("ask_reply", "是")}})
            continue
        if kind == "resp" and m.get("req_id") == rid:
            rec["ok"] = bool(m.get("ok"))
            payload = m.get("payload") if isinstance(m.get("payload"), dict) else {}
            rec["reply"] = payload.get("reply")
            rec["success"] = payload.get("success")
            err = m.get("error")
            rec["error"] = err.get("msg") if isinstance(err, dict) else err
            if rec["ok"]:
                stats["ok"] += 1
            else:
                stats["errors"].append(f"{rid}:{rec['error']}")
            break
    rec["secs"] = round(time.time() - t0, 2)
    records.append(rec)
    print(f"[turn {i + 1}] ok={rec['ok']} success={rec['success']} secs={rec['secs']} reply_len={len(rec['reply'] or '')}", flush=True)

print(json.dumps({"stats": stats}, ensure_ascii=False), flush=True)
if OUT:
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"stats": stats, "turns": records}, f, ensure_ascii=False, indent=2)
