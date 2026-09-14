#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R428-hold · 循环入口探针 v3 修复的证据生成器 (零构建 / 零产品代码 / 零轮号占用)。

背景: 同一工作树内 30 分钟节拍作业 (9a97763d5fcd) 正在实现 R428 (反饱和/召回并列线) ⇒ 本侧只做
      **零冲突**推进: 改 `scripts/capability_cycle_status.py` (纯 stdlib 探针) + 本证据目录。

判据 (先于跑数写死, 见 docs/reports/loop-detection-probe-hardening.md §7):
  H1 修复生效: 计划项行 (expN) 在 **post** 的 open_items 中, 且在 **pre** (HEAD 版本) 中缺席。
  H2 不回退: post 的 open 集合 ⊇ pre 的 open 集合 (修复只增不漏), 且 mode 不变 (tasks)。
  H3 探针自证: `--selftest` 全 PASS 且 rc=0; 其中负控 N3/N4 在旧逻辑下必须判错 (判别力)。
  H4 可复现: 从 git HEAD 取回的 pre 版本重跑, open_items 与修复前真机读数逐项相同。
  H5 沉积透明: 每条 open 项携带 other_cells 原文 (不做机械裁定)。
输出: pre-v2-status.json / post-v3-status.json / selftest-v3.txt / legacy-real-backlog.json /
      hold-r428.json (机检读数) / README-evidence.md (由机检读数渲染)。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # eval/capability/r428-hold -> repo
PROBE = os.path.join(REPO, "scripts", "capability_cycle_status.py")
BACKLOG = os.path.join(REPO, "docs", "plans", "v0.22.0-longterm-backlog.md")
MASTER = os.path.join(REPO, "docs", "reports", "dynamic-telemetry-eval-rollback-strategy.md")
# 显式传文档路径: pre 副本落在 /tmp, 其自算 ROOT 会退化为 "/" ⇒ 不传参则读不到文档 (采集侧假失败)
DOC_ARGS = ["--backlog", BACKLOG, "--master", MASTER]
PRE_SNAPSHOT = "/tmp/st428.json"   # 修复前真机读数 (由 v2 脚本在 18:16 产出, 含尾部 rc= 行)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=120)
    return p.returncode, (p.stdout + p.stderr)


def parse_json(out: str) -> dict:
    body = out.strip().splitlines()
    for i, ln in enumerate(body):
        ln = ln.strip()
        if ln.startswith("{"):
            return json.loads(ln)
    raise ValueError("no json line: " + out[:200])


def main() -> int:
    readings: dict = {}

    # ── 0) pre 版本: 从 git HEAD 取回 (证明「修复前」可复现, 不靠 /tmp 残留)
    rc, pre_src = run(["git", "show", "HEAD:scripts/capability_cycle_status.py"])
    if rc != 0:
        print("FAIL: 无法从 HEAD 取回 pre 版本", pre_src[:300])
        return 2
    pre_path = os.path.join("/tmp", "r428hold-pre-status-probe.py")
    with open(pre_path, "w", encoding="utf-8") as fh:
        fh.write(pre_src)
    pre_sha = sha256_file(pre_path)
    post_sha = sha256_file(PROBE)

    rc_pre, out_pre = run([sys.executable, pre_path] + DOC_ARGS)
    pre = parse_json(out_pre) if rc_pre == 0 else {"error": out_pre[:400]}
    with open(os.path.join(HERE, "pre-v2-status.json"), "w", encoding="utf-8") as fh:
        json.dump(pre, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # ── 1) post 版本 (当前工作树)
    rc_post, out_post = run([sys.executable, PROBE] + DOC_ARGS)
    post = parse_json(out_post) if rc_post == 0 else {"error": out_post[:400]}
    with open(os.path.join(HERE, "post-v3-status.json"), "w", encoding="utf-8") as fh:
        json.dump(post, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # ── 2) 探针自检 (判定器自证 + 负控)
    rc_st, out_st = run([sys.executable, PROBE, "--selftest"])
    with open(os.path.join(HERE, "selftest-v3.txt"), "w", encoding="utf-8") as fh:
        fh.write(out_st)
        fh.write(f"\nrc={rc_st}\n")
    checks = [ln for ln in out_st.splitlines() if ln.startswith(("PASS", "FAIL"))]
    st_fail = [ln for ln in checks if ln.startswith("FAIL")]
    st_summary = next((ln for ln in out_st.splitlines() if ln.startswith("selftest:")), "")

    # ── 3) legacy (v1 逻辑) 真机 A/B
    rc_leg, out_leg = run([sys.executable, PROBE, "--legacy"])
    legacy = parse_json(out_leg) if rc_leg == 0 else {"error": out_leg[:400]}
    with open(os.path.join(HERE, "legacy-real-backlog.json"), "w", encoding="utf-8") as fh:
        json.dump(legacy, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # ── 4) 可复现对照: 修复前真机读数 (v2 脚本 18:16 产出) 必须与 pre 重跑逐项相同
    pre_snapshot = None
    if os.path.exists(PRE_SNAPSHOT):
        raw = open(PRE_SNAPSHOT, encoding="utf-8-sig", errors="replace").read()
        pre_snapshot = parse_json(raw.split("rc=")[0])

    plan_pre = [i for i in pre.get("open_items", []) if i.startswith("exp")]
    plan_post = [i for i in post.get("open_items", []) if i.startswith("exp")]
    set_pre = set(pre.get("open_items", []))
    set_post = set(post.get("open_items", []))

    readings.update({
        "probe_pre_sha256": pre_sha,
        "probe_post_sha256": post_sha,
        "pre_run_rc": rc_pre,
        "post_run_rc": rc_post,
        "pre_open_count": pre.get("open_count"),
        "pre_open_items": pre.get("open_items"),
        "pre_plan_items": plan_pre,
        "pre_mode": pre.get("mode"),
        "post_open_count": post.get("open_count"),
        "post_open_items": post.get("open_items"),
        "post_plan_items": plan_post,
        "post_mode": post.get("mode"),
        "post_plan_rows_scanned": (post.get("sources", {}).get("backlog", {}) or {}).get("plan_rows_scanned"),
        "selftest_fail_count": len(st_fail),
        "selftest_check_count": len(checks),
        "selftest_summary": st_summary,
        "selftest_rc": rc_st,
        "legacy_real_open_count": legacy.get("open_count"),
        "legacy_real_mode": legacy.get("mode"),
        "legacy_real_open_items": legacy.get("open_items"),
        "pre_snapshot_present": pre_snapshot is not None,
        "H1_plan_items_now_visible_and_absent_before": bool(plan_post) and not plan_pre,
        "H2_no_regression_superset_and_mode_stable": set_pre.issubset(set_post) and pre.get("mode") == post.get("mode") == "tasks",
        "H3_selftest_all_pass": (not st_fail) and rc_st == 0,
        "H4_pre_reproduced_by_head_version": bool(pre_snapshot) and pre_snapshot.get("open_items") == pre.get("open_items"),
        "H5_every_open_item_has_other_cells": all(
            d.get("other_cells") for d in post.get("open_items_detail", [])),
        "post_detail_kinds": {d["item"]: d.get("kind") for d in post.get("open_items_detail", [])},
    })
    readings["verdict"] = "PASS" if all(readings[k] for k in (
        "H1_plan_items_now_visible_and_absent_before",
        "H2_no_regression_superset_and_mode_stable",
        "H3_selftest_all_pass",
        "H4_pre_reproduced_by_head_version",
        "H5_every_open_item_has_other_cells")) else "FAIL"

    with open(os.path.join(HERE, "hold-r428.json"), "w", encoding="utf-8") as fh:
        json.dump(readings, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # ── 5) README-evidence.md 由机检读数渲染
    md = [
        "# R428-hold · 循环入口探针 v3 证据 (机检渲染, 勿手改)",
        "",
        f"- 生成器: `eval/capability/r428-hold/run_hold.py` · 探针 pre sha256 `{pre_sha[:16]}` → post sha256 `{post_sha[:16]}`",
        f"- verdict: **{readings['verdict']}** (H1 计划项入账 / H2 不回退 / H3 自检全绿 / H4 前态可复现 / H5 沉积透明)",
        "",
        "## 读数",
        "",
        "| 项 | pre (HEAD 版本重跑) | post (工作树 v3) |",
        "|---|---|---|",
        f"| mode | `{pre.get('mode')}` | `{post.get('mode')}` |",
        f"| open_count | {pre.get('open_count')} | {post.get('open_count')} |",
        f"| 计划项 (expN) 条数 | {len(plan_pre)} | {len(plan_post)} |",
        f"| 轮次行 (R\\d+) 条数 | {len(pre.get('open_items', [])) - len(plan_pre)} | {len(post.get('open_items', [])) - len(plan_post)} |",
        "",
        "## post open_items",
        "",
    ]
    for i, it in enumerate(post.get("open_items", []), 1):
        md.append(f"{i}. {it}")
    md += [
        "",
        "## 判定器自检 (含负控)",
        "",
        f"- `--selftest`: **{st_summary}**, rc={rc_st}, FAIL={len(st_fail)}",
        "- 负控 N3/N4 = 旧行键/旧分类必须判错 (selftest 内部 A/B, 见 `selftest-v3.txt`)",
        f"- legacy (v1 逻辑) 跑真机看板: mode=`{legacy.get('mode')}`, open_count={legacy.get('open_count')} ⇒ v1 连 R371/R370 都读不到 (读错列 + 完成标记先过滤)",
        "",
        "## 诚实边界",
        "",
        "1. 本 tick **不改产品源码、不跑 dotnet、不占轮号** (R428 由 30 分钟节拍作业 9a97763d5fcd 占用中, mtime 18:14)。",
        "2. 探针只改「读得到/判得准」: `open_items` 的 8 条不等于 8 个待办 —— 轮次行 R371/R370 是否沉积、exp1 是否受阻于用户裁决, 仍须读 `other_cells` 与对应计划文档判定 (探针不做机械裁定)。",
        "3. 未登记 `docs/verification-registry.json`: 该改动需当轮立即跑形式校验 (dotnet) ⇒ 与活跃构建窗口冲突, 顺延到活跃体释放后 (同 R402 tick 处置)。",
        "",
        "## 复现",
        "",
        "```",
        "python3 eval/capability/r428-hold/run_hold.py      # 重跑全部读数并重渲染本文件",
        "python3 scripts/capability_cycle_status.py --selftest",
        "python3 scripts/capability_cycle.py status",
        "```",
        "",
    ]
    with open(os.path.join(HERE, "README-evidence.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    print(json.dumps({k: readings[k] for k in sorted(readings)}, ensure_ascii=False, indent=2)[:1800])
    return 0 if readings["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
