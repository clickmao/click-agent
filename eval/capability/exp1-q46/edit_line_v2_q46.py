#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q46 二部: 把 §7 块那行的**路径引用写显式**（v1 → v2）。

动因（机检驱动）: 替代机检 subst_check_q46.py 对 v1 行报 rc=2 —— 行内写了裸文件名
(`scan-pre.txt` / `scan-post.txt` / `improvements.md`) 而机检按**根相对**解析 ⇒ 解析失败。
纪律（R435）: 引用歧义时**改文档把引用写显式**，**不放宽判据**。

同样纪律: 锚点由产物自身派生 ∧ 唯一性 fail-closed ∧ 幂等 ∧ 行级不变量 ∧ 读回校验。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DOC = os.path.join(ROOT, "docs", "reports", "dynamic-telemetry-eval-rollback-strategy.md")

STALE_KEY = "（rc=0，见该目录"      # 必须**前态独有**（首版用了一个在 v2 文本里仍保留的短语
#                                    ⇒ 「旧键已消失」恒假 = 器具恒红; 机检: 前态计数=1 ∧ 后态计数=0）
NEW_KEY = "eval/capability/r518/scan-pre.txt"     # v2 行独有
NEW_LINE = (
    ">   - **另一本台账（improvements.md 轮节，EXP1-Q45 已闭合）**: 该本台账的 8 处轮节已由 "
    "**EXP1-Q45**（`1ef590a`）逐节补齐并机检化 —— `eval/capability/r518/scan_round_sections.py`：前态 "
    "C1 n=8（R402/R404/R405/R406/R407/R417/R418/R419，rc=1）→ 后态 C1 n=0 ∧ ZONE 13→21（rc=0，读数见 "
    "`eval/capability/r518/scan-pre.txt` / `eval/capability/r518/scan-post.txt`）；`docs/improvements.md` "
    "自陈更正见其 R404 段（旧口径作废留痕）。原括注范围「R404–R416」与机检缺集不符（真缺集跨 R402–R419）"
    "⇒ 以机检为准。**记录面时效（EXP1-Q46 机检）**: 上方「最近一轮」字段停在 R509 / `0b88277`，而现盘 HEAD "
    "= `29f75c3`（R518，13:29）⇒ 该字段归**主线轮收口**刷新，本 tick 只登记不代写（防与对侧写者撞车）。"
)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(DOC):
        print("CHK file=FALSE"); print("EDIT2_EXIT=3"); return 3

    raw = open(DOC, "rb").read()
    lines = raw.decode("utf-8").splitlines(keepends=True)
    stale = [i for i, ln in enumerate(lines) if STALE_KEY in ln]
    has_new = any(NEW_KEY in ln for ln in lines)
    print(f"CHK v1_candidates n={len(stale)} at={stale}  v2_present={has_new}")

    if has_new and not stale:
        print(f"CHK idempotent=TRUE sha16={sha(raw)}")
        print("EDIT2_EXIT=0 IDEMPOTENT_SKIP"); return 0
    if len(stale) != 1:
        print("CHK v1_anchor_unique=FALSE (fail-closed)"); print("EDIT2_EXIT=2"); return 2

    i = stale[0]
    out = list(lines)
    out[i] = NEW_LINE + ("\n" if lines[i].endswith("\n") else "")
    if len(out) != len(lines) or any(out[j] != lines[j] for j in range(len(lines)) if j != i):
        print("CHK line_invariant=FALSE"); print("EDIT2_EXIT=2"); return 2

    new_txt = "".join(out)
    print(f"CHK target_line_no={i + 1} sha16_before={sha(raw)} after={sha(new_txt.encode('utf-8'))}")
    print(f"CHK line_count={len(lines)} (unchanged)")
    if a.dry_run:
        print("EDIT2_EXIT=0 DRY_RUN"); return 0

    with open(DOC, "wb") as fh:
        fh.write(new_txt.encode("utf-8"))
    back = open(DOC, "rb").read().decode("utf-8")
    ok = (NEW_KEY in back) and (STALE_KEY not in back)
    print(f"CHK readback_v2_present={NEW_KEY in back} v1_gone={STALE_KEY not in back} sha16={sha(back.encode('utf-8'))}")
    if not ok:
        print("EDIT2_EXIT=2 READBACK_MISMATCH"); return 2
    print("EDIT2_EXIT=0 APPLIED"); return 0


if __name__ == "__main__":
    sys.exit(main())
