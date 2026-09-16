#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R506 · 候选④ 闭合: 把 r433 冻结行的 evidence_cmd 补成**可完整重放**的命令。

缺口 (R504 报告 行 27/19 登记, 原文): 「行 2 重放缺口 1 行未闭合 (行 2 的 evidence_cmd 缺 baseline
文件名 glob)」——`probe-m6-agent.json` 是冻结台账 §一 的 #0 行, 而行自带 glob `*r433*` 覆盖不到它。

本工具只改**一个字段** (evidence_cmd), 且:
  ① 改前断言 OLD 串在原文中**恰好出现 1 次** (不猜、不模糊匹配);
  ② 改后断言 json 语义 = 「仅该字段变了」的对象级比对 (不重排整份 JSON);
  ③ 改后断言行数不变 ∧ 逐行 diff 只落在含 `"evidence_cmd"` 的那一行 (R409 纪律: 不静默重排);
  ④ 幂等: 再跑一次（OLD 已不存在）⇒ 判为**已闭合**, 零改动退出 0;
  ⑤ 新增两条 R2b 语义断言: 新命令引用的仓库路径全部存在 ∧ 派生器具与行声明**一致**
     (bind_evidence 的 instrument_from_cmd 取「首个存在且带源码扩展名」的路径 ⇒ 必须是 grade.py)。

用法:
  python3 eval/rover/r506/close_row2_replay_gap.py --check
  python3 eval/rover/r506/close_row2_replay_gap.py --apply
退出码: 0 成功/已闭合; 1 断言失败(拒绝落盘); 3 输入缺失。
"""
import argparse
import io
import json
import os
import re
import sys

REG = "docs/verification-registry.json"
ROW_ID = "r433.probe-code-source-artifact-channel"

KPI_STAGE_OLD = ("python3 scripts/kpi_probe.py --glob 'data/probe/probe-*r433*.json' "
                 "--report eval/capability/r433/kpi-report.md")
KPI_STAGE_NEW = ("python3 scripts/kpi_probe.py --run data/probe/probe-m6-agent.json "
                 "--glob 'data/probe/probe-*r433*.json' "
                 "--compare probe-m6-agent.json probe-agent-seed0-r433m6fix2.json "
                 "--report eval/capability/r433/kpi-report.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--registry", default=REG)
    a = ap.parse_args()
    if not os.path.isfile(a.registry):
        print("[致命] 登记表缺失 %s" % a.registry)
        return 3
    raw = io.open(a.registry, encoding="utf-8", newline="").read()
    doc = json.loads(raw)
    rows = [r for r in doc["rows"] if r.get("id") == ROW_ID]
    if len(rows) != 1:
        print("[致命] 行定位失败 n=%d" % len(rows))
        return 3
    row = rows[0]
    cur = row.get("evidence_cmd") or ""
    have_old = cur.count(KPI_STAGE_OLD)
    have_new = cur.count(KPI_STAGE_NEW)

    print("[state] 旧阶段串出现 %d 次 · 新阶段串出现 %d 次" % (have_old, have_new))
    if have_new == 1 and have_old == 0:
        print("[已闭合] 该行 evidence_cmd 已含 baseline+compare (幂等, 零改动)")
        return 0
    if have_old != 1:
        print("[致命] 旧阶段串出现 %d 次 (期望 1) —— 拒绝改写" % have_old)
        return 1

    want_raw = raw.replace(KPI_STAGE_OLD, KPI_STAGE_NEW, 1)
    if want_raw == raw:
        print("[致命] 替换后字节未变")
        return 1

    # 断言 ① 语义等价 (只该字段变)
    want = json.loads(want_raw)
    expect = json.loads(raw)
    for r in expect["rows"]:
        if r.get("id") == ROW_ID:
            r["evidence_cmd"] = cur.replace(KPI_STAGE_OLD, KPI_STAGE_NEW, 1)
    if want != expect:
        print("[致命] 写入对象 != 期望 (拒绝落盘)")
        return 1

    # 断言 ② 逐行 diff 限界
    lo, ln = raw.splitlines(), want_raw.splitlines()
    if len(lo) != len(ln):
        print("[致命] 行数变化 %d -> %d" % (len(lo), len(ln)))
        return 1
    changed = [i for i, (x, y) in enumerate(zip(lo, ln)) if x != y]
    if len(changed) != 1 or "evidence_cmd" not in ln[changed[0]]:
        print("[致命] 越界改动行: %s" % [i + 1 for i in changed])
        return 1

    # 断言 ③ 新命令引用的仓库路径全部存在 (R2b 语义, 与 CmdPath 白名单一致)
    new_cmd = want["rows"][[i for i, r in enumerate(want["rows"]) if r.get("id") == ROW_ID][0]]["evidence_cmd"]
    cmd_paths = re.findall(r"(?<![\w/.-])((?:src|scripts|eval|docs|tests|website)/[A-Za-z0-9_./-]+)", new_cmd)
    missing = [p for p in cmd_paths if not os.path.exists(p)]
    if missing:
        print("[致命] 新命令引用不存在的路径 %s" % missing)
        return 1

    # 断言 ④ 派生器具 == 行声明 (bind_evidence.instrument_from_cmd 的同一规则)
    SRC_EXT = (".py", ".cs", ".sh", ".ps1")
    declared = (row.get("evidence_generated_with") or {}).get("instrument")
    derived = next((p for p in cmd_paths if p.endswith(SRC_EXT) and os.path.isfile(p)), None)
    if derived != declared:
        print("[致命] 派生器具 %r != 行声明 %r (改命令不得改变器具归属)" % (derived, declared))
        return 1

    print("[plan] 目标行 %d · 引用路径 %s 全存在 · 派生器具 %s == 声明" % (changed[0] + 1, cmd_paths, derived))
    print("[plan] 旧: %s" % cur)
    print("[plan] 新: %s" % new_cmd)
    if a.check:
        return 0
    io.open(a.registry, "w", encoding="utf-8", newline="").write(want_raw)
    again = io.open(a.registry, encoding="utf-8", newline="").read()
    if again != want_raw:
        print("[致命] 写后字节不一致")
        return 1
    print("[OK] evidence_cmd 已闭合 (改动行 %d)" % (changed[0] + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
