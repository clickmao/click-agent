#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q46 预注册判据裁定 (P3/P4/P7b/P8 + P2 机检), 逐条 CHK + 显式退出码。"""
from __future__ import annotations

import json
import os
import sys

D = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(D, name), encoding="utf-8-sig") as fh:
        return json.load(fh)


def rd(name):
    with open(os.path.join(D, name), encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


pre = load("status_pre.json")
post = load(sys.argv[1] if len(sys.argv) > 1 else "status_post.json")
nc = load("status_nc_prestate.json")
rc = 0
checks = []


def chk(name, cond, extra=""):
    global rc
    checks.append((name, bool(cond), extra))
    if not cond:
        rc = 2


# P2 盘面证伪
scan = rd("scan_now.txt")
chk("P2_scanner_rc0", "SCAN_RC=0" in scan and "SCAN_EXIT=0" in scan)
chk("P2_c1_missing_zero", "C1 MISSING n=0" in scan)
# P3 后态预测
chk("P3_master_open_zero", post["master_open"] == 0, f"mode={post['mode']}")
chk("P3_route_backlog", post["route"]["primary"] == "backlog", post["route"]["primary"])
chk("P3_first_exp1", str(post["route"]["first"]).startswith("exp1"), str(post["route"]["first"])[:60])
chk("P3_open_count_8", post["open_count"] == 8, f"open_count={post['open_count']}")
# P4 不变量: backlog 面逐字不变
back_pre = [i for i in pre["open_items"]][: pre["backlog_open"]]
back_post = [i for i in post["open_items"]][: post["backlog_open"]]
chk("P4_backlog_open_8", post["backlog_open"] == 8 == pre["backlog_open"])
chk("P4_backlog_items_identical", back_pre == back_post)
# 块结构不变量
chk("P4_block_fields_29", post["sources"]["master"]["block_fields"] == 29 == pre["sources"]["master"]["block_fields"],
    f"{post['sources']['master']['block_fields']}")
chk("P4_block_found", post["sources"]["master"]["block_found"] is True)
# P7b 前态锚臂 (复现假开放项)
chk("P7b_nc_master_open_1", nc["master_open"] == 1, f"hits={nc['sources']['master']['hits']}")
chk("P7b_nc_route_master_block", nc["route"]["primary"] == "master-block")
chk("P7b_nc_first_stale", "另一本台账" in str(nc["route"]["first"]))
# P8 探针自检
st = rd("selftest_post.txt")
chk("P8_selftest_34", "34/34 passed" in st and "SELFTEST_RC=0" in st)

print("┌─ EXP1-Q46 预注册裁定")
for n, ok, extra in checks:
    print(f"│ {'PASS' if ok else 'FAIL'}  {n}  {extra}")
print(f"└─ VERIFY_EXIT={rc}  (checks={len(checks)}, pass={sum(1 for _, o, _ in checks if o)})")
print(f"CHK pre_master_hits={pre['sources']['master']['hits']} "
      f"post_master_hits={post['sources']['master']['hits']} "
      f"pre_close_fenced={pre['sources']['master']['close_fenced']} "
      f"post_close_fenced={post['sources']['master']['close_fenced']} "
      f"post_quoted_fenced={post['sources']['master']['quoted_fenced']}")
print(f"CHK post_route_first={str(post['route']['first'])[:70]}")
print(f"CHK nc_route_first={str(nc['route']['first'])[:70]}")
sys.exit(rc)
