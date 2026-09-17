#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q44 · D9 判据器 (前态锚 = commit cc9cafc 字节, 非 HEAD; 三道独立读数).

判据 (D9 = 两条非状态形态围栏: 闭合陈述 / 引用形态):
  P7  真仓 master 面假阳性被消: master hits 3 -> 2, 且 route.first 不再是「R401–R412 逐轮回填…关闭」行
  P8  围栏计数可见: close_fenced >= 1 ∧ quoted_fenced >= 1 (不是静默丢弃)
  P9  真开放项未被误围栏: improvements.md 的 R404–R416 轮节行**仍在** open_items
  P10 前态锚(cc9cafc)复现假阳性: 同一真仓上该版 master hits == 3 (成对 ⇒ 判别力);
      且断言 cc9cafc 是 HEAD 的祖先 ∧ 其字节与现盘不同 (防「钉 HEAD」的静默失效)
  P11 作用域: backlog 面读数 (backlog_open / backlog 项) 两版逐字相同 (改动只落在 master 面)
rc: 0 过 / 1 预注册不满足 / 2 器具缺陷 / 3 缺输入
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PRE_ANCHOR = "cc9cafc"          # D9 之前最后一次提交 (= D8 落地), 钉 sha 不钉 HEAD


def load(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8-sig", errors="replace") as fh:
        return json.load(fh)


def sh(*args) -> str:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="D9 判据器")
    ap.add_argument("--out", default="verdict_q44_d9.json")
    ap.add_argument("--ns", default="", help="命名空间/说明 (重测单列, 不覆盖首测)")
    ap.add_argument("--expect-hits", default="3,2",
                    help="P7 期望 (pre,post) master hits; 语料被有意改写时随语料重算并在 ns 里说明")
    args = ap.parse_args()
    exp_pre, exp_post = (int(x) for x in args.expect_hits.split(","))
    pre, post = load("status_v5_D8.json"), load("status_v5d9.json")
    lr = load("status_v5d9_legacyroute.json")
    if pre is None or post is None or lr is None:
        print(json.dumps({"rc": 3, "why": "missing_inputs"}, ensure_ascii=False))
        return 3
    for r, name in ((pre, "status_v5_D8.json"), (post, "status_v5d9.json"), (lr, "status_v5d9_legacyroute.json")):
        if "route" not in r:
            print(json.dumps({"rc": 2, "why": "route_field_absent (器具缺陷)", "which": name},
                             ensure_ascii=False))
            return 2
    if "close_fenced" not in post["sources"]["master"]:
        print(json.dumps({"rc": 2, "why": "close_fenced_absent (器具缺陷: 现盘探针未输出围栏计数)"},
                         ensure_ascii=False))
        return 2

    checks = []

    def chk(name, cond, got):
        checks.append({"check": name, "ok": bool(cond), "got": got})

    def m_items(r):
        return r["open_items"][r["backlog_open"]:]

    pre_hits, post_hits = pre["sources"]["master"]["hits"], post["sources"]["master"]["hits"]
    chk("P7 真仓假阳性被消: master hits 3->2 ∧ route.first 不再是「R401–R412…关闭」行",
        pre_hits == exp_pre and post_hits == exp_post
        and "R401–R412 逐轮回填" not in (post["route"]["first"] or ""),
        {"pre_hits": pre_hits, "post_hits": post_hits, "post_first": (post["route"]["first"] or "")[:80],
         "expected": [exp_pre, exp_post]})
    chk("P8 围栏计数可见 (close_fenced>=1 ∧ quoted_fenced>=1), 非静默丢弃",
        post["sources"]["master"]["close_fenced"] >= 1
        and post["sources"]["master"]["quoted_fenced"] >= 1,
        {"close_fenced": post["sources"]["master"]["close_fenced"],
         "quoted_fenced": post["sources"]["master"]["quoted_fenced"]})
    chk("P9 真开放项未被误围栏 (improvements.md R404–R416 行仍在 open_items)",
        any("R404–R416" in i for i in m_items(post)), m_items(post))
    ancestor = sh("git", "merge-base", "--is-ancestor", PRE_ANCHOR, "HEAD") or "0"
    rc_anc = subprocess.run(["git", "merge-base", "--is-ancestor", PRE_ANCHOR, "HEAD"],
                            cwd=ROOT).returncode
    bytes_pre = sh("git", "show", f"{PRE_ANCHOR}:scripts/capability_cycle_status.py")
    with open(os.path.join(ROOT, "scripts", "capability_cycle_status.py"), encoding="utf-8") as fh:
        bytes_now = fh.read()
    chk(f"P10 前态锚 ({PRE_ANCHOR}) 复现假阳性 (>=3) ∧ 是 HEAD 祖先 ∧ 字节与现盘不同",
        pre_hits >= 3 and rc_anc == 0 and bytes_pre != bytes_now,
        {"pre_hits": pre_hits, "is_ancestor": rc_anc == 0, "bytes_differ": bytes_pre != bytes_now})
    chk("P11 作用域: backlog 面 (backlog_open + backlog 项) 逐字相同 ⇒ 改动只落 master 面",
        pre["backlog_open"] == post["backlog_open"]
        and pre["open_items"][:pre["backlog_open"]] == post["open_items"][:post["backlog_open"]],
        {"backlog_open": (pre["backlog_open"], post["backlog_open"])})
    chk("P11b 负控(--legacy-route) 在 D9 版上仍为 backlog (D9 不改路由优先序)",
        lr["route"]["primary"] == "backlog", {"legacy_route_primary": lr["route"]["primary"]})

    fails = [c for c in checks if not c["ok"]]
    verdict = {
        "round": "EXP1-Q44", "artifact": "scripts/capability_cycle_status.py v5/D9",
        "pre_anchor_sha": PRE_ANCHOR, "supersedes_for": ["sources.master.hits", "open_items(master 段)"],
        "rc": 1 if fails else 0, "checks": checks,
        "readings": {
            "pre_hits": pre_hits, "post_hits": post_hits,
            "close_fenced": post["sources"]["master"]["close_fenced"],
            "quoted_fenced": post["sources"]["master"]["quoted_fenced"],
            "post_master_items": m_items(post), "post_route_first": post["route"]["first"],
        },
        "note": "P2(D8) 的「共享字段逐字相同」只成立于 D8 快照; D9 有意变更 master 面语义 ⇒ 不翻案, 单列",
        "ns": args.ns,
        "supersedes_first_measurement": bool(args.ns),
    }
    with open(os.path.join(HERE, args.out), "w", encoding="utf-8") as fh:
        json.dump(verdict, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    for c in checks:
        print(f"{'PASS' if c['ok'] else 'FAIL'}  {c['check']}  got={json.dumps(c['got'], ensure_ascii=False)[:200]}")
    print(f"verdict_d9 rc={verdict['rc']} ({len(checks) - len(fails)}/{len(checks)})")
    return verdict["rc"]


if __name__ == "__main__":
    sys.exit(main())
