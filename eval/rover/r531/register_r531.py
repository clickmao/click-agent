#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R531 登记表追加 (文本插入, 禁静默重排整份 JSON)。

纪律 (R409 教训): ① 改写前先断言「序列化器逐字节复现原文件」; ② 只补**前一行**的逗号, 末行之后不加;
③ 幂等; ④ 改写后读回校验 + json.loads 全文件。
"""
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
P = os.path.join(REPO, "docs/verification-registry.json")

ROWS = [
    {
        "id": "internal.wythoff-independent-oracle-r531",
        "level": "L4",
        "capability": "**F1 非同源判据器 (R531)**: 手写「必败点 DP + 暴力枚举合法着法」独立 oracle, 对 wythoff 族 15 条冻结用例重算期望并与夹具 `expected_stdout` 逐字节比对, 再对四臂产出逐例分类 (`canonical` / `illegal_move` / `wrong_lose` / `wrong_win` / `not_winning`) 。读数: 独立 oracle 与冻结期望 **15/15 完全一致** ⇒ **夹具无缺陷**; A0-off 13/15 (`#43 (21,25)` 出 `WIN 1 13`、`#57 (25,25)` 出 `WIN 2 11`, 皆 `illegal_move` = 取两堆不等量, 题面只允许单堆取或等量双取) · A1-on 13/15 (`#55 (1,1)`、`#57 (25,25)` 皆 `LOSE` = `wrong_lose`, 漏 `(t,t)` 双取分支) · A2-merge 15/15 · codex 15/15 ⇒ R531 的 `exec_precondition` rc=1 属**能力缺陷**, 非夹具缺陷。",
        "covers": ["eval/rover/r531/oracle_wythoff_r531.py", "eval/rover/r531/evidence/oracle-wythoff-r531.json",
                   "eval/rover/r531/cases/cases-r521.json", "eval/rover/r531/snapshots/w1/",
                   "eval/rover/r507pre/precondition-r531.json"],
        "evidence_cmd": "python3 eval/rover/r531/oracle_wythoff_r531.py --json eval/rover/r531/evidence/oracle-wythoff-r531.json  (rc=0)",
        "evidence_path": "eval/rover/r531/evidence/oracle-wythoff-r531.json",
        "evidence_generated_with": {"evidence_kind": "artifact", "pin_status": "frozen",
                                  "pin_reason": "archived-per-round", "artifact_sha12": "717fa6c2ee47",
                                  "instrument": "eval/rover/r531/oracle_wythoff_r531.py", "instrument_sha12": "812a1422d491",
                                  "binding": "audit-pin", "audited_by_round": "R531"},
        "negative_control": "`--neg-control` rc=0 且两针皆响: ① NC1 把首条 wythoff 用例期望篡改为错值 ⇒ `fixture_agrees=False` (不一致被检出, disagreements=1); ② NC2 令 oracle 分类非法着法 `WIN 1 2` @(21,25) ⇒ 必须为 `illegal_move` (实测 True) ⇒ 判据器非恒真、非恒假。",
        "owner_round": "R531",
    },
    {
        "id": "internal.merge-axis-mount-r531",
        "level": "L4",
        "capability": "**合批轴挂载证明器 v2 (R531)**: 只读**实发** system prompt 归档, 证明单变量 env `AGENTFRAMEWORK_ACTION_MERGE` 真接上 —— M1 前缀关系 (`A1-on` 的 system 是 `A2-merge` 的前缀) · M2 差量**逐字节等于**从源码抽取的 `ActionLoopDiscipline.MergeText` 全文 (132 字, 两侧 sha12 同为 `9be41f32e862`) · M3 `A0-off` 无纪律块 · M4 三臂共有前缀锚。读数: 9,434 / 9,968 / 10,100 字, `MOUNT_OK=true` ⇒ 合批臂的读数可归因到第 7 条, 而非「未接上的空轴」。",
        "covers": ["eval/rover/r531/mount_check_r531.py", "eval/rover/r531/evidence/mount-r531-w1.json",
                   "src/agent.modelqueue/ActionLoopDiscipline.cs", "eval/rover/r531/run-0917-213234/adapter/"],
        "evidence_cmd": "python3 eval/rover/r531/mount_check_r531.py --run-dir eval/rover/r531/run-0917-213234  (rc=0)",
        "evidence_path": "eval/rover/r531/evidence/mount-r531-w1.json",
        "evidence_generated_with": {"evidence_kind": "artifact", "pin_status": "frozen",
                                  "pin_reason": "archived-per-round", "artifact_sha12": "9377d2c67190",
                                  "instrument": "eval/rover/r531/mount_check_r531.py", "instrument_sha12": "60830eb89354",
                                  "binding": "audit-pin", "audited_by_round": "R531"},
        "negative_control": "`--neg-control` rc=0 且两针皆响: ① NC1 把 A1/A2 角色对调 (以合批臂为基线) ⇒ M1/M2 判红; ② NC2 同臂自比 (差量为空) ⇒ M2 判红。另: M2 不信正则, 用逐字符扫描抽 `MergeText` (文本含 `;`/转义时正则截断, 本次实测截断值 66 ≠ 132 ⇒ 已修为扫描器)。",
        "owner_round": "R531",
    },
    {
        "id": "internal.r531-cross-window-aggregate",
        "level": "L3",
        "capability": "**R531 跨窗聚合器**: 把 `evidence/windows/<win>/report.json` 聚成「每臂每窗 calls / 新算 prompt / completion / 命中率 / 质量」+ 轴比值 (合批 vs 纪律开 / vs 关 · 纪律开 vs 关) + **跨窗极差**, 窗数 <3 ⇒ verdict 自动标 provisional。读数 (3 窗, 同轮同二进制 `d5848776…`): merge/on calls = **0.881 (w1) / 1.429 (w2) / 0.488 (w3)**, median 0.881, **极差 2.93×**; merge/off 0.65 / 3.158 / 0.362; 三窗质量合计 A1-on **352/354** > codex 350/354 > A2-merge **349/354** > A0-off 339/354 ⇒ 「合批轴降调用」**未证稳定增益** (2/3 窗同向, 1/3 反向)。本器只做窗间对比, **禁跨轮相减**。",
        "covers": ["eval/rover/r531/aggregate_r531.py", "eval/rover/r531/evidence/kpi-r531-windows.json",
                   "eval/rover/r531/evidence/windows/", "eval/rover/r531/prereg-r531.json"],
        "evidence_cmd": "python3 eval/rover/r531/aggregate_r531.py --json eval/rover/r531/evidence/kpi-r531-windows.json  (rc=0; 3 窗)",
        "evidence_path": "eval/rover/r531/evidence/kpi-r531-windows.json",
        "evidence_generated_with": {"evidence_kind": "artifact", "pin_status": "frozen",
                                  "pin_reason": "archived-per-round", "artifact_sha12": "946f9747921e",
                                  "instrument": "eval/rover/r531/aggregate_r531.py", "instrument_sha12": "6a4126f4da84",
                                  "binding": "audit-pin", "audited_by_round": "R531"},
        "negative_control": "**无专用 `--neg-control` 开关 (诚实登记, 不冒充)**: 反恒真由三条结构性保证 —— ① 无窗 ⇒ `AGG_RC=3` fail-closed (不输出任何比值) ② 某臂在该窗缺席 ⇒ 该臂标缺、比值置 `null` 且**不参与极差** (禁以 0 冒充) ③ 只读冻结 `report.json`, 不重算、不回写。窗数 <3 时 verdict 强制 `provisional`, 防单窗冒充结论。",
        "owner_round": "R531",
    },
]


def main():
    raw = io.open(P, encoding="utf-8").read()
    doc = json.loads(raw)
    have = {r["id"] for r in doc["rows"]}
    todo = [r for r in ROWS if r["id"] not in have]
    if not todo:
        print("幂等: 全部 id 已在册 (%d 行), 无操作" % len(doc["rows"]))
        return 0

    canon = json.dumps(doc, ensure_ascii=False, indent=1)
    serializer_roundtrip = (canon.rstrip("\n") == raw.rstrip("\n"))
    print("序列化器逐字节复现原文件 =", serializer_roundtrip, "(不成立 ⇒ 禁整份重写, 仅文本插入)")

    anchor = '  }\n ],\n'
    if raw.count(anchor) != 1:
        print("[致命] 插入锚点不唯一 (count=%d) ⇒ 停手" % raw.count(anchor))
        return 3
    lines = []
    for idx, r in enumerate(todo):
        for ln in json.dumps(r, ensure_ascii=False, indent=1).split("\n"):
            lines.append("  " + ln)
        if idx != len(todo) - 1:
            lines[-1] += ","
    block = "\n".join(lines) + "\n"
    new = raw.replace(anchor, "  },\n" + block + " ],\n")
    if new == raw:
        print("[致命] 文本插入未生效 ⇒ 停手")
        return 3
    new = new.replace('"updated_round": "R529"', '"updated_round": "R531"')

    io.open(P, "w", encoding="utf-8", newline="\n").write(new)

    back = json.loads(io.open(P, encoding="utf-8").read())
    print("读回校验: rows %d → %d, updated_round=%s" % (len(doc["rows"]), len(back["rows"]), back["updated_round"]))
    ids = [r["id"] for r in back["rows"]]
    ok = all(r["id"] in ids for r in todo) and len(ids) == len(set(ids))
    print("新增 id 在册 =", ok, "| 无重复 id =", len(ids) == len(set(ids)))
    for r in todo:
        got = [x for x in back["rows"] if x["id"] == r["id"]][0]
        same = all(got.get(k) == v for k, v in r.items())
        print("  字段逐项一致:", r["id"], same)
    if not ok:
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
