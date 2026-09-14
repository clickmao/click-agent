#!/usr/bin/env python3
"""R413 任务驱动器 — 通过 frontend-api (JSON Lines / TCP) 驱动真链跑固定任务脚本。

契约 (src/agent.frontendapi/FrontendApiContract.cs):
  请求 {"v":1,"type":"req","req_id":"r1","api":"chat.send","payload":{"text":"..."}}
  响应 {"v":1,"type":"resp","req_id":"r1","ok":true,"payload":{"reply":...,"success":...}}
  事件 {"v":1,"type":"event","event":"...","payload":{...}}
用法: python3 -u drive_task.py <port> <task.json> [out.jsonl]
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

# R358 鉴权握手: 首行必须 {"type":"auth","token":"..."}。服务端静默接受 (无应答),
# 且 auth 与首请求整流合并也不丢 (R376 残包回灌) —— 这里显式分行发送, 语义最清晰。
TOKEN = os.environ.get("AGENTFRAMEWORK_FRONTEND_TOKEN", "")
if TOKEN:
    sock.sendall((json.dumps({"type": "auth", "token": TOKEN}) + "\n").encode("utf-8"))
    time.sleep(0.2)
stats = {"turns": 0, "ok": 0, "events": 0, "asks": 0, "errors": []}


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


records = []
for i, turn in enumerate(TASK["turns"]):
    rid = f"t{i + 1}"
    stats["turns"] += 1
    t0 = time.time()
    send({"v":1, "type":"req", "req_id": rid, "api":"chat.send", "payload":{"text": turn}})
    rec = {"turn": i + 1, "text": turn, "reply": None, "ok": None, "events": [], "secs": None,
           "t_start": round(t0, 4)}  # R423: 绝对时间戳 ⇒ 远端调用可按时间窗精确归属到轮 (修 R418「归属缺失」教训)
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
                send({"v":1, "type":"req", "req_id": f"a{i + 1}",
                      "api": "ask.reply", "payload": {"ask_id": ask_id, "text": TASK.get("ask_reply", "是")}})
            continue
        if kind == "resp" and m.get("req_id") == rid:
            rec["ok"] = bool(m.get("ok"))
            payload = m.get("payload") if isinstance(m.get("payload"), dict) else {}
            rec["reply"] = payload.get("reply")
            rec["success"] = payload.get("success")
            rec["error"] = (m.get("error") or {}).get("msg") if isinstance(m.get("error"), dict) else m.get("error")
            if rec["ok"]:
                stats["ok"] += 1
            else:
                stats["errors"].append(f"{rid}:{rec['error']}")
            break
    rec["secs"] = round(time.time() - t0, 2)
    rec["t_end"] = round(time.time(), 4)  # R423: 轮结束绝对时间 ⇒ 与桩侧调用 ts 对窗口
    records.append(rec)
    print(f"[turn {i + 1}] ok={rec['ok']} secs={rec['secs']} reply_len={len(rec['reply'] or '')}", flush=True)

print(json.dumps({"stats": stats}, ensure_ascii=False), flush=True)
if OUT:
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"stats": stats, "turns": records}, f, ensure_ascii=False, indent=2)
