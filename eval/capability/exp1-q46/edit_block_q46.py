#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q46 记录面闭合编辑器 (行锚派生, 幂等, fail-closed, 读回校验)。

纪律 (与 EXP1-Q40/Q45 同族):
  * 锚点**由产物自身派生** (定位 `<...另一本台账...` 行), 不手打长字面量 (手打会被写入通道改写);
  * 锚点唯一性 fail-closed: 命中数 != 1 ⇒ rc=2, 绝不猜;
  * 幂等: 新行已在 ∧ 锚点已无 ⇒ IDEMPOTENT_SKIP rc=0, 文件零字节变化;
  * 只替换该行, 其余行**逐字节**保留 (行级比对, 不用整份重排);
  * 读回校验: 不采信工具回执 —— 重读文件断言 新行在 ∧ 锚点无 ∧ 行数不变;
  * 退出码分层: 0 成功/幂等; 2 器具缺陷(锚点不唯一/读回不符); 3 环境(文件缺失)。

用法: python3 edit_block_q46.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DOC = os.path.join(ROOT, "docs", "reports", "dynamic-telemetry-eval-rollback-strategy.md")

ANCHOR_KEY = "未在本轮动"          # 派生键: 只**前态行**含此串 (与 NEW_LINE 不相交 —— 首跑曾用「另一本台账」
#                                   作键, 而该串在新文本里也出现 ⇒ 读回 readback_anchor_gone 恒假 = 器具假红)
NEW_KEY = "EXP1-Q45 已闭合"
NEW_LINE = (
    ">   - **另一本台账（improvements.md 轮节，EXP1-Q45 已闭合）**: 该本台账的 8 处轮节已由 "
    "**EXP1-Q45**（`1ef590a`）逐节补齐并机检化 —— `eval/capability/r518/scan_round_sections.py`：前态 "
    "C1 n=8（R402/R404/R405/R406/R407/R417/R418/R419，rc=1）→ 后态 C1 n=0 ∧ ZONE 13→21（rc=0，见该目录 "
    "`scan-pre.txt` / `scan-post.txt`）；`improvements.md` 自陈更正见其 R404 段（旧口径作废留痕）。"
    "原括注范围「R404–R416」与机检缺集不符（真缺集跨 R402–R419）⇒ 以机检为准。"
    "**记录面时效（EXP1-Q46 机检）**: 上方「最近一轮」字段停在 R509 / `0b88277`，而现盘 HEAD = `29f75c3`"
    "（R518，13:29）⇒ 该字段归**主线轮收口**刷新，本 tick 只登记不代写（防与对侧写者撞车）。"
)
NEW_KEY = "EXP1-Q45 已闭合"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(DOC):
        print("CHK file=FALSE")
        print("EDIT_EXIT=3")
        return 3

    raw = open(DOC, "rb").read()
    txt = raw.decode("utf-8")
    lines = txt.splitlines(keepends=True)

    hit_idx = [i for i, ln in enumerate(lines) if ANCHOR_KEY in ln]
    has_new = any(NEW_KEY in ln for ln in lines)
    print(f"CHK anchor_candidates n={len(hit_idx)} at={hit_idx}")
    print(f"CHK new_line_present={has_new}")

    if has_new and not hit_idx:
        print(f"CHK idempotent=TRUE sha16={sha(raw)}")
        print("EDIT_EXIT=0 IDEMPOTENT_SKIP")
        return 0

    if len(hit_idx) != 1:
        print("CHK anchor_unique=FALSE (fail-closed: 锚点命中数 != 1, 拒绝改写)")
        print("EDIT_EXIT=2")
        return 2

    i = hit_idx[0]
    old_line = lines[i]
    newline_ending = "\n" if old_line.endswith("\n") else ""
    replacement = NEW_LINE + newline_ending
    # 行级不变量: 除该行外其余行逐字节相同, 行数不变
    out_lines = list(lines)
    out_lines[i] = replacement
    assert len(out_lines) == len(lines)
    for j, (x, y) in enumerate(zip(lines, out_lines)):
        if j != i and x != y:
            print(f"CHK other_line_changed=TRUE line={j + 1}")
            print("EDIT_EXIT=2")
            return 2

    new_txt = "".join(out_lines)
    print(f"CHK target_line_no={i + 1} old_len={len(old_line)} new_len={len(replacement)}")
    print(f"CHK line_count_before={len(lines)} after={len(out_lines)}")
    print(f"CHK sha16_before={sha(raw)} after={sha(new_txt.encode('utf-8'))}")

    if a.dry_run:
        print(f"CHK dry_run=TRUE new_line={NEW_LINE[:80]}…")
        print("EDIT_EXIT=0 DRY_RUN")
        return 0

    with open(DOC, "wb") as fh:            # 写回无 BOM 的 UTF-8 (与读端 utf-8-sig 兼容)
        fh.write(new_txt.encode("utf-8"))

    # ── 读回校验 (不采信回执) ──
    back = open(DOC, "rb").read()
    back_lines = back.decode("utf-8").splitlines(keepends=True)
    ok = (NEW_KEY in back.decode("utf-8")) and (not any(ANCHOR_KEY in ln for ln in back_lines)) \
        and len(back_lines) == len(lines) and back != raw
    print(f"CHK readback_new_present={NEW_KEY in back.decode('utf-8')}")
    print(f"CHK readback_anchor_gone={not any(ANCHOR_KEY in ln for ln in back_lines)}")
    print(f"CHK readback_line_count_ok={len(back_lines) == len(lines)}")
    print(f"CHK readback_sha16={sha(back)}")
    if not ok:
        print("EDIT_EXIT=2 READBACK_MISMATCH")
        return 2
    print("EDIT_EXIT=0 APPLIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
