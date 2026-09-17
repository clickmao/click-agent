#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R511 审批通道真机探针 (TCP / JSON Lines, 契约见 FrontendApiContract.cs + FrontendPromptService)。

流程: auth → chat.send(真链真模型, 指令删除文件) → 收事件; 见到 `approval.requested`
      就按 --approve 回 `approval.respond{approval_id,approved}` → 收 chat.send 响应 →
      落盘 {"events":..., "response":..., "snapshot":..., "victim_exists":bool, "secs":x}。

用法: python3 probe_frontend_approval.py --port 48681 --out /tmp/r511/e2e/approve.json \
        --approve true --victim /tmp/r511/e2e/ws/victim.txt --text "…"
"""
from __future__ import annotations
import argparse, json, os, socket, sys, time


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--victim", required=True)
    ap.add_argument("--approve", default="true")
    ap.add_argument("--text", default="")
    ap.add_argument("--timeout", type=float, default=300.0)
    a = ap.parse_args()
    approve = a.approve.strip().lower() in ("1", "true", "yes")
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

    text = a.text or ("工作区里有一个文件 victim.txt。请用 delete_file 工具删除它，" 
                      "删除后只回一句：已删除 victim.txt。")
    out = {"events": [], "asks": 0, "approvals": [], "approve_requested": approve,
           "secs": None, "text": text, "victim": a.victim}
    t0 = time.time()
    send({"v": 1, "type": "req", "req_id": "r1", "api": "chat.send", "payload": {"text": text}})
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
            ev = m.get("event")
            out["events"].append({"event": ev, "payload": p})
            if ev == "approval.requested" and p.get("approval_id"):
                out["approvals"].append(p)
                out["events"].append({"event": "probe.approval_reply_sent",
                                      "payload": {"approval_id": p["approval_id"], "approved": approve}})
                send({"v": 1, "type": "req", "req_id": "ap1", "api": "approval.respond",
                      "payload": {"approval_id": p["approval_id"], "approved": approve,
                                  "reason": "r511-e2e"}})
                continue
            if p.get("ask_id"):
                out["asks"] += 1
                send({"v": 1, "type": "req", "req_id": "a1", "api": "ask.reply",
                      "payload": {"ask_id": p["ask_id"], "text": "是"}})
            continue
        if m.get("type") == "resp" and m.get("req_id") == "r1":
            out["response"] = {"ok": m.get("ok"), "payload": m.get("payload"), "error": m.get("error")}
            break
    out["secs"] = round(time.time() - t0, 2)
    out["victim_exists"] = os.path.exists(a.victim)
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
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    names = [e["event"] for e in out["events"]]
    print(f"PROBE secs={out['secs']} approvals={len(out['approvals'])} victim_exists={out['victim_exists']} "
          f"events={names} resp_ok={(out.get('response') or {}).get('ok')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
