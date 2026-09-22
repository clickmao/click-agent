#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R641 登记面写入（幂等）：registry 行 + kpi 行。

纪律（memory 铁律）：
  · 改写前断言「序列化器逐字节复现原文件」（registry: indent=1 / ensure_ascii=False / tail=LF）；
  · JSON 插入只补「前一行的逗号」，末行后不加逗号；
  · 脚本**幂等**（重跑不重复插入）；
  · 改写后**读回校验**（重跑 checked 断言 + 打印写入区域）。
"""
from __future__ import annotations
import hashlib
import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
REG = os.path.join(REPO, "docs/verification-registry.json")
KPI = os.path.join(REPO, "eval/capability/kpi.jsonl")

ROW_ID = "r641.wythoff-line-level-attribution"

capability = (
    "承重缺口族 `wythoff` **行级定因闭合 + 判据面分辨率条款**（零产品源码改动 / 零重测 / 零新臂 / 零远端 / "
    "零新增夹具语义）。冻结面 = R639 w237/w238/w239 × {agentP-r1..r3, codex} **12 跑次**（只读副本执行）。"
    "**J4 合计 5/5 定因（R640 遗留「未定因 4/5」⇒ 0/5 闭合）**：单行臂 3/5 CONFIRMED（`w237/agentP-r3` 冷集索引 "
    "12→15 · `w238/agentP-r3` 帧表示 12→15 · `w239/codex` 着法合法性 13→15）＋ **联合臂 2/2 CONFIRMED**"
    "（`w239/agentP-r1` 4→15 · `w239/agentP-r2` 3→15；两跑次均为**合成缺陷**，单行实验必然 NO_EFFECT/PARTIAL）。"
    "**J5 分辨率条款（本仓首次登记）**：采样面（15 例）是规格面（25×25=625 格）的**稀疏子集** ⇒ 见证式构造得"
    "采样面 **15/15** 全绿 ∧ 规格面 **610/625 判红**，反向控制（去掉 1 个采样位置）采样面 **14/15 转红**。"
    "**J3 帧感知分类（暴露上位器具缺陷）**：新增类 `FRAME_TRANSPOSE`（输出着法的**转置**为必胜着法）= 表示面缺陷，"
    "`w238/agentP-r3` **3/3**、`w239/agentP-r2` 1 ⇒ R640 判据器把这批误标为 `nonwinning_move`（帧不感知）。"
    "**其余判据**：J0 正控 15/15 ∧ 变异 13/15 判红 · J1 重放↔**机取期望表**（R639 判决件族级 + R640 第二源）"
    "`mismatch=0` · J2 守恒 **696=696** · 空重写负控 **7/7** 与 base 逐位相同且仍红 · J8 确定性 12/12 逐位相同 · "
    "J9 非平凡性 **7 个互异签名**/12。**自捕器具缺陷 4 条**（E1 J5 mutant 自身抛异常 · E2 无增量落盘致读数丢失 · "
    "E3 J9 tuple join · E4 v1 mutant 在 25×25 面**结构上不可触发**＝空心），全部**先修器具再加读数**、未放宽断言；"
    "v1 未产出任何读数 ⇒ 无翻案。**rc=0**（全部预注册判据成立）。"
)

negative_control = (
    "成对/负向控制（现场执行，读数入 `out/attrib-r641.json` / `out/joint-r641.json`）："
    "① **J0 oracle 两侧有牙** —— 正控 15/15（防恒红）∧ 变异（(6,10) 必败位翻转）13/15 判红（防恒绿）；"
    "② **空重写负控 7/7**（v1 未证「凡改即绿」的反面）—— 同字节重写同一文件 ⇒ 三族读数与 base **逐位相同** ∧ 目标族仍 < 15；"
    "③ **最小修复实验的差分方向两侧都有** —— 目标族转绿（+）**且**其余三族逐例**不变**（`others_unchanged=True`，排除「凡改必全绿」与「改动外溢」）；"
    "④ **J5 分辨率条款两侧样例** —— 见证体（采样面专用解）采样 15/15 ∧ 规格面 610/625 判红（正控：采样面不能自证规格面）"
    "∧ 反向控制（去掉 1 个采样位置 ⇒ 采样面 14/15，证明采样面读数**不是恒绿**）；"
    "⑤ **J1 期望表两源 fail-closed** —— 主源 R639 判决件族级 ∧ 次源 R640 `per_run_wythoff`，不符即 rc=2 器具层（缺源 rc=3），"
    "**禁手写期望表**（承 R640 E1）；⑥ **确定性 ∧ 非平凡性成对** —— J8 12/12 逐位相同（必要条件）**且** J9 跨跑次签名 7 个互异"
    "（防恒定输出冒充可复现）；⑦ **增量落盘断点续跑的自证** —— 三次运行（v1 崩 / v2 修 J9 崩 / v3 全绿）中 v2 复用 replay+J4 缓存"
    "后仍得**逐位相同**的 J1/J2 读数 ⇒ 缓存不引入漂移。"
)

note = (
    "轮次工件: eval/rover/r641/{dag-r641.md,prereg-r641.json,attrib_r641.py,joint_r641.py} + out/{attrib-r641.json,"
    "joint-r641.json,attrib-log-r641.txt} + 断点续跑缓存（.cache-replay-r641.json / .cache-j4-r641.json）。"
    "**预注册时序如实标注**：`written_before_run=false`（v2 进程先起）· `declared_before_any_reading=true`"
    "（落盘时 out/ 仅存 v1 traceback 日志、盘上读数 0 件）；J4b 联合臂另有 addendum，**先于该臂起臂**落盘。"
    "**起手闸 P3 内存读数 FAIL 如实入档**（2550 MB @3000MB / 2605 MB @2900MB；R639 台账 REQ≈2727 MB），"
    "本轮为只读轮 ⇒ 该闸保护对象未触发、**未调闸值**。跳步「构建/AOT」（零 src 改动）与「铁律 11 前置器」"
    "[covers 叙述（R2c：covers 只许放存在路径，叙述移入本段）] 冻结题集 sha256 270128eb…（与 r610/r639 逐字节一致）；"
    "期望表两源机取（r639 verdict.B_family_block ∧ r640 attrib.per_run_wythoff），不符 rc=2 / 缺源 rc=3；"
    "行级锚点逐字取自现盘源码且断言替换次数 == 1（缺失 ⇒ ANCHOR_MISS fail-closed）；"
    "只读：一切执行在副本上进行，零写入冻结树（PYTHONDONTWRITEBYTECODE=1）。"
    "（无真机臂无降幅宣称），显式声明非跳步掩盖。**跨轮禁相减**：本轮零新跑次，不与 R639 `D=[−3,0,−9]` 亦不与 R640 任何读数相减。"
)

EVID = "docs/evidence/RF0001/R641-line-level-attribution-and-resolution-clause.md"


def w(path):
    return io.open(path, "w", encoding="utf-8", newline="\n")


def insert_registry_row():
    raw = io.open(REG, encoding="utf-8").read()
    d = json.loads(raw)
    _covers = [
        "eval/rover/r641/dag-r641.md",
        "eval/rover/r641/prereg-r641.json",
        "eval/rover/r641/attrib_r641.py",
        "eval/rover/r641/joint_r641.py",
        "eval/rover/r641/out/attrib-r641.json",
        "eval/rover/r641/out/joint-r641.json",
        "eval/rover/r622/wythoff_oracle.py",
        "eval/rover/r639/cases/cases-r521.json",
        "eval/rover/r641/register_r641.py",
        "docs/evidence/RF0001/R641-line-level-attribution-and-resolution-clause.md",
    ]
    _pin = hashlib.sha256(io.open(os.path.join(REPO, EVID), "rb").read()).hexdigest()[:12]
    assert len(_pin) == 12
    missing = [c for c in _covers if not os.path.exists(os.path.join(REPO, c))]
    assert not missing, "R2C_PRECOMPUTE_FAIL: covers 含不存在路径 %s" % missing
    assert all(("/" in c and not c.endswith("…")) for c in _covers)
    assert json.dumps(d, indent=1, ensure_ascii=False) + "\n" == raw, "SER_ASSERT_FAIL: 序列化器未逐字节复现原文件"
    ids = [r["id"] for r in d["rows"]]
    upsert = ROW_ID in ids
    row = {
        "id": ROW_ID,
        "level": "L3",
        "owner_round": "R641",
        "capability": capability,
        "evidence_cmd": ("python3 eval/rover/r641/attrib_r641.py && python3 eval/rover/r641/joint_r641.py && "
                         "python3 -c \"import io,json;d=json.load(io.open('eval/rover/r641/out/attrib-r641.json'));"
                         "j=json.load(io.open('eval/rover/r641/out/joint-r641.json'));"
                         "print(d['J4_summary'],d['J5_resolution_clause']['pass'],j['summary'])\" && "
                         "python3 eval/capability/status_gen.py --check && python3 eval/capability/decl_sweep.py --check"),
        "evidence_path": EVID,
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "frozen",
            "pin_reason": "archived-per-round",
            # 冻结 pin = **本件自身现盘字节** sha256[:12]（R2e）；改证据文件必须定向重审。
            # 选 frozen 而非 live 的理由：live 行不带 artifact_sha12 ⇒ roundcheck R4 取
            # `str(None)` 判红（**roundcheck R4 的 live 分支缺陷**，R639 至今同样红）⇒ 冻结可绕开该缺陷
            # 且不放松任何判据（冻结是**更强**约束：字节漂移会被逐字比对）。
            "artifact_sha12": hashlib.sha256(io.open(os.path.join(REPO, EVID), "rb").read()).hexdigest()[:12],
            "instrument": "eval/rover/r641/attrib_r641.py",
            "instrument_sha12": "1155ea55e8e4",
            "binding": "audit-pin",
            "audited_by_round": "R641",
        },
        "covers": _covers,
        "negative_control": negative_control,
        "note": note,
    }
    if upsert:
        i = [k for k, r in enumerate(d["rows"]) if r["id"] == ROW_ID][0]
        d["rows"][i] = row
    else:
        d["rows"].append(row)
    d["updated_round"] = "R641"
    out = json.dumps(d, indent=1, ensure_ascii=False) + "\n"
    w(REG).write(out)
    # 读回校验
    back = json.loads(io.open(REG, encoding="utf-8").read())
    got = [r for r in back["rows"] if r["id"] == ROW_ID]
    assert len(got) == 1, "READBACK_FAIL: 行未落盘或被重复插入"
    assert back["updated_round"] == "R641"
    assert json.dumps(back, indent=1, ensure_ascii=False) + "\n" == io.open(REG, encoding="utf-8").read()
    print("[registry] upsert=%s rows=%d updated_round=%s sha12=%s" % (
        upsert, len(back["rows"]), back["updated_round"],
        __import__("hashlib").sha256(out.encode()).hexdigest()[:12]))


def append_kpi_row():
    row = {
        "round": "R641",
        "ts": "2026-09-23T00:20:00+08:00",
        "kind": ("R640 遗留「J4 未定因 4/5」**行级定因闭合** ＋ 判据面**分辨率条款**登记"
                 "（零产品源码改动 / 零重测 / 零新臂 / 零远端 / 零新增夹具语义）；冻结面 = R639 12 跑次，只读副本执行。"
                 "**决策规则**：合成缺陷须以**联合臂**为实验形态（单行必然 NO_EFFECT/PARTIAL）；"
                 "器具缺陷**先修再加读数**、v1 未产出读数故无翻案；起手闸 P3 内存 FAIL 如实入档且只读轮未触发其保护对象。"),
        "change": ("零产品源码改动（跳步 构建/AOT —— 无被测二进制）。器具面新增 2 件："
                   "`attrib_r641.py`（帧感知分类 + 行级/联合最小修复 + 分辨率条款 + 两源机取期望表 + 分块增量落盘）"
                   "与 `joint_r641.py`（J4b 联合臂驱动器）。**它改哪一格读数**：新增的是**定因粒度**"
                   "（族级 → **行级**，并给出合成缺陷的联合实验形态）与**判据器分辨率**（采样面 vs 规格面）"
                   "⇒ 不改任何既有读数、不抬任何既有 KPI。"),
        "readings": ("冻结面 12 跑次（**零新跑次 ⇒ 成本/缓存/调用三列不适用，标「未测」**）："
                     "J0 正控 **15/15** ∧ 变异 **13/15** 判红 · J1 重放↔机取期望表 **mismatch 0** · J2 守恒 **696=696** · "
                     "J3 帧感知分类 新增 `FRAME_TRANSPOSE`（`w238/agentP-r3` **3/3** · `w239/agentP-r2` 1）· "
                     "J4 单行 **3/5 CONFIRMED** · J4b 联合 **2/2 CONFIRMED** ⇒ **J4 合计 5/5（R640 遗留未定因 4/5 ⇒ 0/5）** · "
                     "空重写负控 **7/7** 与 base 逐位相同且仍红 · J5 采样面 **15/15** ∧ 规格面 **610/625 判红** ∧ "
                     "反向控制采样面 **14/15 转红** · J8 确定性 **12/12** · J9 非平凡性 **7 个互异签名**/12。"
                     "**行级读数**：`w237/agentP-r3` 12→15（冷集索引）· `w238/agentP-r3` 12→15（帧表示）· "
                     "`w239/codex` 13→15（着法合法性，**真值臂自身缺陷**）· `w239/agentP-r1` 4→15 · `w239/agentP-r2` 3→15；"
                     "七处实验的**其余三族逐例不变**。"),
        "verdict": ("`rc=0`（**全部预注册判据成立**）：J0/J1/J2/J3/J4b/J5/J8/J9 全 PASS，J4 单行栏 3/5 不构成失败"
                    "（合成缺陷的单行实验必然 NO_EFFECT/PARTIAL，联合臂为正确形态且 **2/2 CONFIRMED**）。"
                    "**本轮无降幅/无质量宣称**（零新跑次、零产品改动）；铁律 11 可执行前置器**不适用**（显式声明）。"
                    "自捕器具缺陷 **4 条**（E1 mutant 自崩 / E2 无增量落盘 / E3 tuple join / E4 v1 mutant 在规格面**结构上不可触发**）"
                    "全部先修器具再加读数、未放宽断言。"),
        "evidence": EVID,
        "prereg": "eval/rover/r641/prereg-r641.json",
        "report": "eval/rover/r641/out/attrib-r641.json",
        "baselines": [
            "F_merge.gate.wythoff_precheck",
            "F_merge.quality.family_block_scan",
            "F_merge.quality.family_lift_min",
            "F_orch.wythoff.pass_r606",
            "F_merge.ld.frozen_list",
            "F_merge.gate.precondition_rc",
        ],
    }
    lines = io.open(KPI, encoding="utf-8").read().splitlines()
    for ln in lines:
        if ln.strip() and json.loads(ln).get("round") == "R641":
            print("[kpi] idempotent skip (round exists)")
            return
    with io.open(KPI, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    back = [json.loads(x) for x in io.open(KPI, encoding="utf-8").read().splitlines() if x.strip()]
    assert back[-1]["round"] == "R641" and len([b for b in back if b.get("round") == "R641"]) == 1
    print("[kpi] appended rows=%d last=%s baselines=%d" % (len(back), back[-1]["round"], len(back[-1]["baselines"])))


if __name__ == "__main__":
    insert_registry_row()
    append_kpi_row()
