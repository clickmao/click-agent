#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R510 前端任务「步进事件」真机探针 (TCP / JSON Lines, 契约见 FrontendApiContract.cs)。

目标: 证明 task.progress **真发** —— 事件里的步号/工具/成败/耗时来自动作环的**真实执行**,
不是"登记了但从不发射"(R509 的欠账), 也不是给 registry 直接喂值的自证。

流程: auth → chat.send (真链真模型 + 动作环开) → 收齐事件/响应 → approval.respond(未知 id) 负控
      → state.snapshot → 落 JSON。
用法: python3 probe_frontend_progress.py --port 48678 --out /tmp/r510/e2e/e2e.json [--text ...]
"""
from __future__ import annotations
import argparse, json, os, socket, sys, time

DEFAULT_TEXT = (
    "在工作区里创建一个文件 r510_progress.txt, 内容写 ok。"
    "然后用 run_command 执行 cat r510_progress.txt 确认内容。最后用一句话说明你做了什么。"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--text", default=DEFAULT_TEXT)
    ap.add_argument("--timeout", type=float, default=300.0)
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

    def request(req_id, api, payload, want_event_pump=True):
        """发请求并读到该 req_id 的 resp; 期间继续泵事件 (asks 自动回 '是')。"""
        send({"v": 1, "type": "req", "req_id": req_id, "api": api, "payload": payload})
        while True:
            line = readline()
            if line is None:
                return None
            try:
                m = json.loads(line)
            except Exception:
                continue
            if m.get("type") == "event":
                if not want_event_pump:
                    out["events"].append({"event": m.get("event"), "payload": m.get("payload") or {}})
                    continue
                p = m.get("payload") if isinstance(m.get("payload"), dict) else {}
                out["events"].append({"event": m.get("event"), "payload": p})
                if p.get("ask_id") and p.get("service"):
                    out["asks"] += 1
                    send({"v": 1, "type": "req", "req_id": "ask-" + str(out["asks"]), "api": "ask.reply",
                          "payload": {"ask_id": p["ask_id"], "text": "是"}})
                continue
            if m.get("type") == "resp" and m.get("req_id") == req_id:
                return {"ok": m.get("ok"), "payload": m.get("payload"), "error": m.get("error")}

    if token:
        send({"type": "auth", "token": token})
        time.sleep(0.2)
    out = {"events": [], "asks": 0, "secs": None, "text": a.text, "ws_files": []}
    t0 = time.time()
    out["response"] = request("r1", "chat.send", {"text": a.text})
    out["secs"] = round(time.time() - t0, 2)

    # 负控: 无待批审批时的 approval.respond 必须显式回 unknown_approval (不得静默当批准)
    out["approval_ctrl"] = request("c1", "approval.respond",
                                   {"approval_id": "apr-doesnotexist", "approved": True})

    # state.snapshot: 断线重连面 — tasks[] 必须带 step_index/current_action
    out["snapshot"] = request("s1", "state.snapshot", {})

    ws = os.environ.get("AGENTFRAMEWORK_WORKSPACE") or os.environ.get("WS_DIR") or ""
    if ws and os.path.isdir(ws):
        out["ws_files"] = sorted(os.listdir(ws))[:20]
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    names = [e["event"] for e in out["events"]]
    prog = [e for e in out["events"] if e["event"] == "task.progress"]
    print(f"PROBE secs={out['secs']} events={names} progress={len(prog)} asks={out['asks']} "
          f"resp_ok={(out.get('response') or {}).get('ok')} ctrl={(out.get('approval_ctrl') or {}).get('payload')} "
          f"ws={out['ws_files']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
