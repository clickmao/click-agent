#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R511 审批通道真机断言器 (fail-closed; 逐条打印 A1.. 并出 verdict)。

用法: python3 assert_e2e_approval.py --approve-json <a.json> --deny-json <d.json> [--json <out.json>]
退出码: 0 全绿 / 1 有假 / 2 输入缺失。
判据 (A1-A9):
  A1 chat.send 响应 ok=true (真答前置)
  A2 审批**通过**臂: 出现 approval.requested 且带 approval_id/kind/summary
  A3 审批**通过**臂: 出现 approval.responded 且 approved=true
  A4 审批通过臂: victim 文件**已被真删** (victim_exists=false) —— 通道闭环的落地证据
  A5 审批**拒绝**臂: victim 文件**仍在** (victim_exists=true)
  A6 拒绝臂: 不得出现 approved=true 的 responded
  A7 回复=真答: reply 非空 且 secs>1.0 (排除 0.01s 陈旧续跑假绿)
  A8 事件序: task.started 早于 task.completed
  A9 审批响应必须由通道产生: requested 与 responded 的 approval_id 一致
"""
from __future__ import annotations
import argparse, json, sys


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--approve-json", required=True)
    ap.add_argument("--deny-json", required=True)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    try:
        ap_ = load(a.approve_json); dn = load(a.deny_json)
    except Exception as e:
        print(f"[致命] 输入缺失/非法: {e}")
        return 2

    checks = []

    def chk(name, ok, detail=""):
        checks.append({"id": name, "ok": bool(ok), "detail": detail})

    def ev_list(x):
        return [e["event"] for e in x.get("events", [])]

    def first(x, name):
        for e in x.get("events", []):
            if e["event"] == name:
                return e["payload"]
        return None

    def recounted(x):
        return [e["payload"] for e in x.get("events", []) if e["event"] == "approval.responded"]

    # A1 真答前置
    r1 = (ap_.get("response") or {})
    r2 = (dn.get("response") or {})
    chk("A1_response_ok", r1.get("ok") is True and r2.get("ok") is True,
        f"approve_ok={r1.get('ok')} deny_ok={r2.get('ok')}")

    # A2 审批通道被真实触发
    pr = first(ap_, "approval.requested")
    chk("A2_approval_requested", pr is not None and bool(pr.get("approval_id")),
        f"approval_id={(pr or {}).get('approval_id')} kind={(pr or {}).get('kind')} summary={(pr or {}).get('summary')}")
    chk("A8_approval_payload_human_readable",
        bool((pr or {}).get("summary")) and bool((pr or {}).get("kind")),
        f"kind={(pr or {}).get('kind')} summary={(pr or {}).get('summary')}")

    # A3/A9 responded 与 requested 对齐
    rd = recounted(ap_)
    ids_match = bool(rd) and bool(pr) and rd[-1].get("approval_id") == (pr or {}).get("approval_id")
    chk("A3_approval_responded_true", bool(rd) and rd[-1].get("approved") is True,
        f"responded={rd[-1] if rd else None}")
    chk("A9_approval_id_roundtrip", ids_match,
        f"requested={(pr or {}).get('approval_id')} responded={rd[-1].get('approval_id') if rd else None}")

    # A4 落地: 文件真被删
    chk("A4_approved_deleted_on_disk", ap_.get("victim_exists") is False,
        f"victim={ap_.get('victim')} exists={ap_.get('victim_exists')}")

    # A5/A6 拒绝臂不得删/不得假批准
    chk("A5_denied_file_intact", dn.get("victim_exists") is True,
        f"victim={dn.get('victim')} exists={dn.get('victim_exists')}")
    dnrd = recounted(dn)
    chk("A6_denied_no_true_approval", not any(x.get("approved") is True for x in dnrd),
        f"deny_responded={dnrd[:2]}")

    # A7 回复=真答 (R509 铁律: 事件全绿而回复陈旧 ⇒ 判红)
    reply = ""
    try:
        payload = (ap_.get("response") or {}).get("payload") or {}
        reply = str(payload.get("reply") or "")
    except Exception:
        reply = ""
    chk("A7_reply_is_real_answer", len(reply.strip()) > 0 and float(ap_.get("secs") or 0) > 1.0,
        f"secs={ap_.get('secs')} reply_len={len(reply.strip())}")

    # A8 事件序
    names = ev_list(ap_)
    order_ok = ("task.started" in names and "task.completed" in names
                and names.index("task.started") < names.index("task.completed"))
    chk("A10_task_event_order", order_ok, f"events={names}")

    verdict = "PASS" if all(c["ok"] for c in checks) else "FAIL"
    for c in checks:
        print(f"[{'PASS' if c['ok'] else 'FAIL'}] {c['id']} {c['detail']}")
    print(f"E2E_APPROVAL_VERDICT={verdict} checks={len(checks)} failed={sum(1 for c in checks if not c['ok'])}")
    if a.json:
        json.dump({"verdict": verdict, "checks": checks}, open(a.json, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
