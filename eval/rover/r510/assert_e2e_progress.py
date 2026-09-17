#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R510 真机 E2E 机械判分 (无模型裁判, 无事后补记)。

判据 (每条独立, 失败即点名; rc 0=全过 / 1=有失败 / 3=输入缺失):
  A1 事件序: task.started → task.progress* → task.completed (单调)
  A2 步进事实: ≥1 条 task.progress 且 step_index≥1 / tool∈声明集 / ok 布尔 / elapsed_ms≥0
  A3 真答: chat.send 响应 ok=true 且 reply 非空
  A4 快照: state.snapshot.tasks 非空且存在 state=done 且 step_index≥1 (断线重连可读)
  A5 审批回程负控: 未知 approval_id → outcome=unknown_approval (绝不静默批准)
  A6 真执行落盘: 工作区出现 ≥1 个文件 (工具真跑了, 不是空转/伪造事件)
用法: python3 assert_e2e_progress.py /tmp/r510/e2e/e2e.json --json /tmp/r510/e2e/assert.json
"""
from __future__ import annotations
import argparse, json, sys

DECLARED_TOOLS = {"list_dir", "read_file", "write_file", "run_command"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    try:
        d = json.load(open(a.dump, encoding="utf-8"))
    except Exception as e:
        print(f"[致命] 无法读取 {a.dump}: {e}")
        return 3

    checks, fails = [], []

    def chk(cid, ok, detail):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})
        if not ok:
            fails.append(cid)

    ev = [(e.get("event"), e.get("payload") or {}) for e in d.get("events", [])]
    names = [n for n, _ in ev]
    prog = [p for n, p in ev if n == "task.progress"]
    i_started = names.index("task.started") if "task.started" in names else -1
    i_first_prog = names.index("task.progress") if "task.progress" in names else -1
    i_done = names.index("task.completed") if "task.completed" in names else -1
    chk("A1", i_started >= 0 and i_first_prog > i_started and i_done > i_first_prog,
        f"事件序 {names} (started={i_started} first_progress={i_first_prog} completed={i_done})")

    if prog:
        bad = [p for p in prog
               if not isinstance(p.get("step_index"), int) or p.get("step_index", 0) < 1
               or p.get("tool") not in DECLARED_TOOLS
               or not isinstance(p.get("ok"), bool)
               or not isinstance(p.get("elapsed_ms"), int) or p.get("elapsed_ms", -1) < 0]
        chk("A2", not bad, f"{len(prog)} 条 progress; 首条={prog[0]}; 非法={bad[:2]}")
    else:
        chk("A2", False, "零 task.progress (登记面到位但发射面未接通)")

    resp = d.get("response") or {}
    rp = resp.get("payload") or {}
    chk("A3", bool(resp.get("ok")) and bool((rp.get("reply") or "").strip()),
        f"resp.ok={resp.get('ok')} reply_len={len((rp.get('reply') or '').strip())}")

    snap = d.get("snapshot") or {}
    sp = snap.get("payload") or {}
    tasks = sp.get("tasks") if isinstance(sp, dict) else None
    ok_tasks = isinstance(tasks, list) and len(tasks) > 0
    ok_done = bool(ok_tasks) and any(t.get("state") == "done" and t.get("step_index", 0) >= 1 for t in (tasks or []))
    chk("A4", bool(snap.get("ok")) and ok_done,
        f"snapshot.ok={snap.get('ok')} tasks={json.dumps(tasks, ensure_ascii=False)[:300]}")

    ctrl = d.get("approval_ctrl") or {}
    cp = ctrl.get("payload") or {}
    chk("A5", bool(ctrl.get("ok")) and cp.get("outcome") == "unknown_approval",
        f"approval_ctrl={json.dumps(ctrl, ensure_ascii=False)[:200]}")

    chk("A6", len(d.get("ws_files") or []) >= 1, f"ws_files={d.get('ws_files')}")

    payload = {"round": "R510", "checks": checks, "fails": fails, "rc": 1 if fails else 0,
               "progress_n": len(prog), "events": names}
    if a.json:
        json.dump(payload, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for c in checks:
        print(f"[{'PASS' if c['ok'] else 'FAIL'}] {c['id']} {c['detail']}")
    print("E2E_ASSERT " + ("PASS" if not fails else "FAIL " + ",".join(fails)))
    return payload["rc"]


if __name__ == "__main__":
    sys.exit(main())
