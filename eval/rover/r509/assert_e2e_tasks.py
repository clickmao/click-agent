#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R509 真机 E2E 断言器 (铁律 11: 产出物可实际执行并正确才可作为对比/验收前置)。

输入 = probe_frontend_tasks.py 的落盘 JSON。全机械判定, 任一不成立 ⇒ rc=1:
  A1 事件流含且仅含 1 个 task.started、1 个 task.completed, 且 started 在前
  A2 task.started 载荷字段: task_id/session_id/started_at_ms/api
  A3 task.completed 载荷字段齐备 + success==true + reply_chars>0
  A4 响应载荷含 task_id, 与 task.started 的 task_id 一致 (同任务不串号; 仅增字段)
  A5 state.snapshot 含 tasks 数组, 且有 state=="done" 任务 (断线重连可读)
负控 (必须为假): A6 事件不得含 payload 泄漏产物路径字段 (paths/artifacts)
用法: python3 assert_e2e_tasks.py <e2e.json> [--json out.json]
"""
from __future__ import annotations
import argparse, json, sys

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("probe")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    d = json.load(open(a.probe, encoding="utf-8"))
    res: dict = {"checks": [], "failed": []}
    def bad(msg):
        res["failed"].append(msg); print("FAIL: " + msg); return 1
    evs = d.get("events") or []
    names = [e.get("event") for e in evs]
    if names.count("task.started") != 1 or names.count("task.completed") != 1:
        return bad(f"A1 started={names.count('task.started')} completed={names.count('task.completed')}")
    if names.index("task.started") > names.index("task.completed"):
        return bad("A1 顺序错")
    res["checks"].append("A1")
    st = [e for e in evs if e["event"] == "task.started"][0]["payload"]
    for k in ("task_id", "session_id", "started_at_ms", "api"):
        if k not in st:
            return bad(f"A2 task.started 缺 {k}")
    res["checks"].append("A2")
    cp = [e for e in evs if e["event"] == "task.completed"][0]["payload"]
    for k in ("task_id", "success", "elapsed_ms", "reply_chars", "steps"):
        if k not in cp:
            return bad(f"A3 task.completed 缺 {k}")
    if cp.get("success") is not True or not (cp.get("reply_chars") or 0) > 0:
        return bad(f"A3 success={cp.get('success')} reply_chars={cp.get('reply_chars')}")
    res["checks"].append("A3")
    rp = ((d.get("response") or {}).get("payload") or {})
    if rp.get("task_id") != st.get("task_id"):
        return bad(f"A4 resp.task_id={rp.get('task_id')!r} != started {st.get('task_id')!r}")
    res["checks"].append("A4")
    snap = ((d.get("snapshot") or {}).get("payload") or {})
    if "tasks" not in snap:
        return bad("A5 snapshot 缺 tasks 字段")
    done = [t for t in (snap.get("tasks") or []) if t.get("state") == "done"]
    if not done:
        return bad("A5 无 state==done 任务")
    if done[-1].get("task_id") != st.get("task_id"):
        return bad("A5 快照终态任务与本次不同")
    res["checks"].append("A5")
    for e in evs:
        for k in ("paths", "artifacts", "artifact_path"):
            if k in (e.get("payload") or {}):
                return bad(f"A6 事件载荷泄漏 {k}")
    res["checks"].append("A6")
    # A7/A8: 防「假绿」——事件域对了但回复是陈旧续跑/空转 (R509 实测踩到: 共享 frontend-main 会话
    # 返回上一轮的续跑追问, 事件面全绿)。真答 + 成功响应才可验收。
    if (d.get("response") or {}).get("ok") is not True:
        return bad(f"A8 响应 ok={(d.get('response') or {}).get('ok')!r} err={(d.get('response') or {}).get('error')!r}")
    res["checks"].append("A8")
    reply = (rp.get("reply") or "").strip()
    if not reply or "2" not in reply:
        return bad(f"A7 回复非真答 (len={len(reply)}): {reply[:80]!r}")
    res["checks"].append("A7")
    res["reply_bytes"] = len(reply)
    res["task"] = done[-1]
    print(f"PASS checks={res['checks']} task_id={done[-1].get('task_id')} elapsed_ms={done[-1].get('elapsed_ms')} "
          f"reply_chars={done[-1].get('reply_chars')} steps={done[-1].get('steps')} events={names} reply={reply[:40]!r}")
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0

if __name__ == "__main__":
    sys.exit(main())
