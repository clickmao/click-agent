#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q44 判据器: 状态探针 v5/D8 的真机 A/B 机检 (预注册 P1/P2/P3/P4 逐条判定).

输入 (全部落在本轮证据目录):
  status_v4.json            = HEAD 版探针 (v4) 在真仓上的读数
  status_v5.json            = 现盘探针 (v5) 在真仓上的读数
  status_v5_legacyroute.json= v5 带 --legacy-route (复现 v4 优先序) 的真仓读数 = 负控
判据 (改动为纯增量 ⇒ 共享字段必须逐字相同):
  P2  共享字段 (mode/open_count/open_items/open_items_detail/backlog_open/master_open/sources) 逐字相同
  P1  真仓 route.primary == 'master-block' ∧ priority[0] 以 'master:' 开头
  P3  负控: --legacy-route 同仓 primary == 'backlog' (与 P1 成对 ⇒ 判别力)
  P4  两侧皆空的回退由 selftest T20/T21 覆盖 (此处只核 priority 长度与实际项数一致)
rc: 0 过 / 1 预注册不满足 / 2 器具缺陷 (读不到/缺字段) / 3 缺输入
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = ["mode", "open_count", "open_items", "open_items_detail",
          "backlog_open", "master_open", "sources"]


def load(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8-sig", errors="replace") as fh:
        return json.load(fh)


def main() -> int:
    v4, v5, lr = load("status_v4.json"), load("status_v5.json"), load("status_v5_legacyroute.json")
    missing = [n for n, v in (("status_v4.json", v4), ("status_v5.json", v5),
                             ("status_v5_legacyroute.json", lr)) if v is None]
    if missing:
        print(json.dumps({"rc": 3, "why": "missing_inputs", "missing": missing}, ensure_ascii=False))
        return 3
    if "route" not in v5 or "route" not in lr:
        print(json.dumps({"rc": 2, "why": "route_field_absent (器具缺陷: 现盘探针未输出 route)"},
                         ensure_ascii=False))
        return 2

    checks = []

    def chk(name, cond, got):
        checks.append({"check": name, "ok": bool(cond), "got": got})

    diffs = {k: {"v4": v4.get(k), "v5": v5.get(k)} for k in SHARED if v4.get(k) != v5.get(k)}
    chk("P2 零回归: 共享字段逐字相同 (纯增量改动)", not diffs, diffs)

    added, removed = sorted(set(v5) - set(v4)), sorted(set(v4) - set(v5))
    chk("P2b 字段集只增不减", not removed, {"added": added, "removed": removed})

    r5, rlr = v5["route"], lr["route"]
    chk("P1 真仓权威源优先: primary=master-block ∧ priority[0]=master:",
        r5["primary"] == "master-block" and r5["priority"][0].startswith("master:"),
        {"primary": r5["primary"], "first": r5["first"], "priority_len": len(r5["priority"])})
    chk("P3 负控(--legacy-route): 同仓 primary=backlog (成对 ⇒ 判别力)",
        rlr["primary"] == "backlog", {"primary_legacy_route": rlr["primary"]})
    chk("P4 priority 项数 == 两侧项数之和 (无静默丢弃)",
        len(r5["priority"]) == v5["backlog_open"] + v5["master_open"],
        {"priority_len": len(r5["priority"]), "backlog_open": v5["backlog_open"],
         "master_open": v5["master_open"]})
    chk("P4b 可比性断点已登记 (route.comparable_from 非空)",
        bool(r5.get("comparable_from")), {"comparable_from": r5.get("comparable_from")})

    fails = [c for c in checks if not c["ok"]]
    verdict = {
        "round": "EXP1-Q44",
        "artifact": "scripts/capability_cycle_status.py v5/D8",
        "rc": 1 if fails else 0,
        "checks": checks,
        "real_repo": {
            "v4_open_items": v4["open_items"], "v5_priority": r5["priority"],
            "master_open": v5["master_open"], "backlog_open": v5["backlog_open"],
        },
    }
    with open(os.path.join(HERE, "verdict_q44.json"), "w", encoding="utf-8") as fh:
        json.dump(verdict, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    for c in checks:
        print(f"{'PASS' if c['ok'] else 'FAIL'}  {c['check']}  got={json.dumps(c['got'], ensure_ascii=False)[:200]}")
    print(f"verdict rc={verdict['rc']} ({len(checks) - len(fails)}/{len(checks)}) -> verdict_q44.json")
    return verdict["rc"]


if __name__ == "__main__":
    sys.exit(main())
