#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R382 D5 真机探针: 以**前端客户端身份**接 FrontendApi, 断言 plan.created/plan.node/plan.finished
真的从服务端推出来 (而不是只存在于内部对象里)。

坑 (R382 实测): socket.makefile() 的 readline() 会绕过 socket 超时**永久阻塞** →
改用 raw recv + 手写断行缓冲。协议: 首行 auth, 之后 {"v":1,"type":"req","req_id":..,"api":..,"payload":..}
"""
import json
import os
import socket
import sys
import time

HOST = "127.0.0.1"
PORT = int(os.environ.get("FE_PORT", "47911"))
TOKEN = os.environ.get("AGENTFRAMEWORK_FRONTEND_TOKEN", "")
PROMPT = os.environ.get(
    "FE_PROMPT",
    "用 Python 开发一个贪吃蛇小游戏(终端, 单文件 snake.py): 逻辑与渲染分离; "
    "无头自测 python3 snake.py --selftest 覆盖 移动/吃食物加分/撞墙判负/计分; "
    "并且统计我这段需求描述的字数。",
)
OUT = os.environ.get("FE_OUT", "/tmp/r382/plan_events.jsonl")
DEADLINE = float(os.environ.get("FE_DEADLINE", "900"))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
events, other = [], []
t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time()-t0:7.1f}s] {msg}", flush=True)


sock = socket.create_connection((HOST, PORT), timeout=30)
sock.settimeout(5)
sock.sendall((json.dumps({"type": "auth", "token": TOKEN}) + "\n").encode())
log("已连接 + auth 已发")
time.sleep(0.5)
for req in ({"req_id": "r-meta", "api": "meta.info"}, {"req_id": "r-hello", "api": "state.hello"}):
    sock.sendall((json.dumps({"v": 1, "type": "req", **req, "payload": {}}) + "\n").encode())
time.sleep(0.5)
sock.sendall((json.dumps({"v": 1, "type": "req", "req_id": "r-chat",
                          "api": "chat.send", "payload": {"text": PROMPT}}) + "\n").encode())
log("chat.send 已发出 (含『统计我这段需求描述的字数』⇒ 应出现无依赖本地节点)")

buf = b""
pending = b""
chat_resp = None
while time.time() - t0 < DEADLINE:
    try:
        chunk = sock.recv(65536)
    except socket.timeout:
        continue
    except OSError as ex:
        log(f"连接异常: {ex}")
        break
    if not chunk:
        log("连接被服务端关闭")
        break
    pending += chunk
    while b"\n" in pending:
        raw_line, pending = pending.split(b"\n", 1)
        raw = raw_line.decode("utf-8", "replace").strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            other.append(raw)
            continue
        if obj.get("type") == "event":
            events.append(obj)
            log(f"event {obj.get('event')} {json.dumps(obj.get('payload'), ensure_ascii=False)[:220]}")
            if obj.get("event") == "plan.finished":
                pass
        else:
            other.append(raw)
            if obj.get("type") == "resp" and obj.get("req_id") == "r-meta":
                log(f"meta.info → {raw[:160]}")
            elif obj.get("type") == "resp" and obj.get("req_id") == "r-chat":
                chat_resp = obj
                log(f"chat.send 响应 ok={obj.get('ok')} payload={json.dumps(obj.get('payload'), ensure_ascii=False)[:200]}")
    if chat_resp is not None and any(e.get("event") == "plan.finished" for e in events):
        break

with open(OUT, "w", encoding="utf-8") as fh:
    for e in events:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")
with open(OUT + ".other", "w", encoding="utf-8") as fh:
    fh.write("\n".join(other))

names = [e.get("event") for e in events]
log(f"共收到事件 {len(events)}: {names}")
missing = [w for w in ("plan.created", "plan.node", "plan.finished") if w not in names]
for want in ("plan.created", "plan.node", "plan.finished"):
    log(f"  {want}: {'✓' if want in names else '✗ 缺失'}")
if chat_resp is None:
    log("✗ chat.send 未收到响应")
sys.exit(1 if (missing or chat_resp is None) else 0)
