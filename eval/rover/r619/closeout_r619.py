#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R619 收口件：registry 行 + kpi 行（幂等）。

承 R618 `closeout_r618.py` 的**机械件**（写前断言「序列化器逐字节复现原文件」+ 行级幂等 + 写后回读断言），
**内容整段重写为 R619 真机读数**（派生副本里的 R618 文本不得沿用 —— 归属篡改风险）。

写入面（两处，均为**共享台账**）：
  ① `docs/verification-registry.json` 追加一行 `r619.exec-face-fallback`（L3）；
  ② `eval/capability/kpi.jsonl` 追加一行（带 `baselines` 11 条 id，RF0004 §4.1 引用义务）。
"""
from __future__ import annotations

import hashlib
import io
import json
import os

ROOT = "/home/agentuser/AgentFramework"
REG = os.path.join(ROOT, "docs/verification-registry.json")
KPI = os.path.join(ROOT, "eval/capability/kpi.jsonl")
RID = "r619.exec-face-fallback"


def sha12(p):
    return hashlib.sha256(io.open(os.path.join(ROOT, p), "rb").read()).hexdigest()[:12]


def sha256f(p):
    return hashlib.sha256(io.open(os.path.join(ROOT, p), "rb").read()).hexdigest()


def registry_add():
    raw = io.open(REG, encoding="utf-8").read()
    doc = json.loads(raw)
    # 程序化改写纪律（R409 实证）：改写前先断言「序列化器逐字节复现原文件」
    if json.dumps(doc, indent=1, ensure_ascii=False) + "\n" != raw:
        print("SER_ASSERT=FAIL ⇒ 拒绝写盘 (fail-closed)")
        return 3
    print("SER_ASSERT=OK (indent=1/ensure_ascii=False/tail=LF)")
    if any(r.get("id") == RID for r in doc["rows"]):
        print("ROW_EXISTS ⇒ 幂等跳过")
        return 0
    art = sha12("eval/rover/r619/report-r619.md")
    inst = sha12("eval/rover/r619/judge_r619.py")
    row = {
        "id": RID,
        "capability": (
            "RF0004.2 · M3 **第三刀 = 空执行面回退**：把「采纳集映射出的执行面为空 ∧ plan 非空」这一**前提**"
            "显式判定出来（纯函数 `ActionExecPlan.Decide`：mapped/plan/present/accepted ⇒ Source·Fallback·UsePlan），"
            "回退读 `plan` 并把**原因码**（`candidates_absent` / `accepted_empty` / `unmapped_all`）落台账 `exec_fallback`；"
            "`ExecSource=plan_fallback`。真机（w211..w213，21 跑次，被测件 sha256 "
            "`a184d7317b6e3c5e2190c792c88da265fdb86da594dde959a2a8389c546424af`，`bin_sha_stable=true`）："
            "① **J0 臂轴生效 PASS** —— T 档面集合 `['candidates']`（⊆ 允许面）∧ C 档**五个受闸字段全缺席 9/9** ∧ "
            "两臂前缀 `prefix_sha256` 同源 `25c97bef…`（= R617 pin，跨轮锚成立，`claims_violated=[]`）；"
            "② **J1（主判据）PASS** —— 面=candidates 9/9 ∧ `executed>0` 9/9 ∧ 条目守恒**违例 0** ∧ "
            "`unmapped` 合计 0 / 期望继承合计 39；③ **J1d PASS（本轮新增）**：`candidates ∧ executed==0` 的"
            "「空转形态」跑次 **0/9**（R618 实测该形态 1/9）；④ **J1e = `NOT_EXERCISED`**：`plan_fallback` 跑次 **0/9** "
            "⇒ **回退分支本轮零行使、机制「未测到」**，三态**不判红也不判 PASS**（禁把未测读成通过）；"
            "⑤ J2b PASS（有声明跑次逐条 `accepted+rejected==declared`，违例 0）；"
            "⑥ 能力面**并列·欠功率**：整题全对 T 6/9=0.6667 vs C 5/9=0.5556 vs codex 真值 **3/3=1.0000**，"
            "逐窗配对差 T−C +0.3333/−0.6667/+0.6667（**极差 1.333 ≫ 池化效应 0.1111**）⇒ 该轴非承重；"
            "⑦ J3 v1 PASS / **J3 v2 FAIL**（`a2_per_window_calls:w212` ∧ `b1_unit_new_prompt`）⇒ **成本面无收益**；"
            "⑧ **铁律 11 rc=1（未可验收）**：`executable_and_correct=false`，blocked 全局 7 / 验收面 28（用例级失败，如 "
            "`w211/agentC-r3 51/58`）⇒ 一切质量/成本读数标「参考（未可验收）」。"
            "**可宣称范围仅 = J0 ∧ J1a ∧ J1b ∧ J1c ∧ J1d ∧ J2b；不可宣称回退机制有效（未行使）亦不可宣称无效。**"),
        "level": "L3",
        "evidence_cmd": (
            "bash eval/rover/r619/run_r619.sh   # 21 跑次（T×9 / C×9 / C1×3），落 $HOME/.agentframework/harness/runs/r619/；"
            "判据器影子自检 8 态: python3 eval/rover/r619/selftest_judge_r619.py（rc=0/checks_failed=[]）；"
            "后处理重算: python3 eval/rover/r619/judge_r619.py --D $HOME/.agentframework/harness/runs/r619 --pd eval/rover/r619；"
            "AOT: bash eval/rover/r619/aot_r619.sh；铁律 11: python3 eval/rover/r507pre/exec_precondition.py --round r619"),
        "evidence_path": "eval/rover/r619/report-r619.md",
        "negative_control": (
            "① **判据器影子自检 8 态**（`eval/rover/r619/selftest_judge_r619.py`，合成台账，`checks_failed=[]`）："
            "A 正常 / B **两臂不可区分**（C 档也带受闸字段 ⇒ J0 判红且 defects 点名）/ C **真空**（T 全缺席 ⇒ J1 fail-closed 不可判）/ "
            "D **守恒违例**（`executed>accepted−unmapped` ⇒ J1b 红且非真空）/ E **跨轮锚不成立**（只记 `claims_violated`，钉住「判据面 vs 宣称面」分离）/ "
            "**F 回退行使且真干活 ⇒ 必须绿（`EXERCISED_OK`）/ G 回退命中而执行面仍空 ⇒ 必须红（`EXERCISED_EMPTY`）/ H D1 形态 ⇒ 必须红**"
            "（三态均保留 rep1 = candidates ∧ executed>0 ⇒ 被隔离的是 J1d/J1e 本身，非 J1a）；"
            "② **同轮轴关负控**：C 档（`AGENTFRAMEWORK_R1_ACTION_EXEC` unset）逐跑次**五个受闸字段缺席 9/9** ⇒ 「轴关 = 旧行为」由机检保证；"
            "③ **AOT 生产档装载冒烟两档**（轴 off / 轴 on）各 rc=0，轴 on 档可见 `exec_source=candidates` 而 `exec_fallback` **缺席** ⇒ "
            "零回归不变式在冒烟面成立；④ **单测零回归条**：`ActionFallbackTests.零回归`（轴关 ⇒ 两字段皆不落）；"
            "⑤ **铁律 11 fail-closed**：blocked 非空 ⇒ rc=1（不得 rc=0 假绿）；⑥ **器具自捕缺陷 I1**（由影子自检 F 态当场抓到）："
            "新键只进 `EXEC_FIELDS` 未进读取契约 `TR_FIELDS` ⇒ 白名单外键静默读空 ⇒ `reason_set=[]` 假红；两处并入后 8 态全绿。"),
        "covers": ["eval/rover/r619/dag-r619.md", "eval/rover/r619/prereg-r619.json",
                   "eval/rover/r619/report-r619.md", "eval/rover/r619/run_r619.sh",
                   "eval/rover/r619/judge_r619.py", "eval/rover/r619/selftest_judge_r619.py",
                   "eval/rover/r619/derive_judge_r619.py", "eval/rover/r619/derive_selftest_r619.py",
                   "eval/rover/r619/aot_r619.sh", "eval/rover/r619/repin_api_r619.sh",
                   "eval/rover/r619/taskset-r619.json", "eval/rover/r619/bins-r619.json",
                   "eval/rover/r619/gate-margin-r619.json", "eval/rover/r619/kpi-table-r619.json",
                   "eval/rover/r619/verdict-r619.json", "eval/rover/r619/cases/run_cases_r521.py",
                   "eval/rover/r619/cases/cases-r521.json",
                   "src/agent/r1/ActionExecPlan.cs", "src/agent/r1/R1Pipeline.cs",
                   "src/agent/r1/R1Transcript.cs", "src/agent/r1/R1RunResult.cs",
                   "src/agent.tests/ActionFallbackTests.cs"],
        "owner_round": "R619",
        "updated_round": "R619",
        "note": (
            "轴**默认 off、未放行**（关闭态由逐跑次字段缺席 9/9 + 单测逐位双钉）。第三刀的**回退分支本轮零行使**"
            "（`plan_fallback` 0/9，`NOT_EXERCISED`）——9/9 治疗档跑次均映射出非空执行面 ⇒ 回退前提从未成立；"
            "下轮须先造「映射面为空 ∧ plan 非空」的可命中窗（**禁改判据阈值**）。铁律 11 首跑 `missing_case_script` 21 臂为"
            "**假阻断**（证据布局缺件：本轮 `cases/` 未随派生器复制，runner 取的正本是 `eval/rover/r610/cases/`）⇒ "
            "逐字节补齐后**只重跑后处理**（零重测），原读数保留于 `precond-r619.layout-gap.json`。"
            "M3 出口闸（调用数去重 ≤ 旧臂 50%）只作读数（分母跨形态不同源，禁相减）。"),
        "evidence_generated_with": {
            "evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
            "artifact_sha12": art, "instrument": "eval/rover/r619/judge_r619.py",
            "instrument_sha12": inst, "binding": "audit-pin", "audited_by_round": "R619"},
    }
    doc["rows"].append(row)
    doc["updated_round"] = "R619"
    io.open(REG, "w", encoding="utf-8").write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    back = json.loads(io.open(REG, encoding="utf-8").read())
    assert back["rows"][-1]["id"] == RID and back["updated_round"] == "R619"
    print("REGISTRY_ADD=OK rows=%d new_id=%s artifact_sha12=%s instrument_sha12=%s"
          % (len(back["rows"]), RID, art, inst))
    return 0


def kpi_add():
    ts = os.popen("date '+%Y-%m-%dT%H:%M:%S%z'").read().strip()   # 真实时钟，禁占位
    row = {
        "round": "R619",
        "ts": ts,
        "kind": ("RF0004.2 · M3 第三刀 = 空执行面回退 真机臂 w211..w213（21 跑次）：机制面 **PASS**"
                 "（rc=0/mechanism_rc=0：J0 两臂可区分 ∧ 前缀与 R617 pin 逐位同 ∧ J1a 面=candidates 9/9 ∧ "
                 "J1b 守恒违例 0 ∧ J1d 空转形态 0/9），**但 J1e=NOT_EXERCISED：回退分支本轮零行使 ⇒ 机制「未测到」**；"
                 "能力面并列·欠功率（整题全对 T 6/9 vs C 5/9 vs 真值 3/3，逐窗 +0.333/−0.667/+0.667，极差 1.33）；"
                 "成本面无收益（J3 v2 FAIL）；铁律 11 rc=1 ⇒ 一切读数**参考（未可验收）**"),
        "change": ("产品侧最小改动 + 器具：① 回退判定抽为**纯函数** `ActionExecPlan.Decide(mapped, plan, present, accepted)`"
                   "（三态原因码 candidates_absent / accepted_empty / unmapped_all）；② 唯一接线点 `R1Pipeline.cs`："
                   "`face.UsePlan ? sem.Plan : map.Steps`（轴关 ⇒ 与 sem.Plan 逐位等价）；③ 台账新增 `exec_fallback`"
                   "（**仅回退时落字段** ⇒ 轴关/未回退时与 R618 逐字节同）；④ 单测 `ActionFallbackTests` 7 条（含零回归条）；"
                   "⑤ 判据器 `judge_r619.py` 增 J1d（形态清零）+ J1e（三态，仅 EXERCISED_EMPTY 判红）；"
                   "⑥ 影子自检扩到 8 态（新增 F/G/H 反向控制）；⑦ **器具自捕缺陷 I1**：新键只进 EXEC_FIELDS 未进读取契约 "
                   "TR_FIELDS ⇒ 白名单外键静默读空 ⇒ F 态假红，**由影子自检当场抓到**，两处并入后 8 态全绿。"
                   "**前缀零改动**：r1gen 未动 ⇒ T/C 两档 prefix_sha256 均 25c97bef…（= R617 pin）"),
        "readings": {
            "real_arms": ("21 跑次（T×9 / C×9 / C1×3）；窗集 w211..w213（与历史 w184..w210 不相交）；"
                          "被测件 sha256 a184d7317b6e3c5e2190c792c88da265fdb86da594dde959a2a8389c546424af（19,838,192 B）"
                          "∧ bin_sha_stable=true；题集 sha256 逐字节复制件 e0c667c2a313c04b…；"
                          "起手闸首试 fail-closed（ceiling 2687−GATE 2650=37MB<60MB，**零臂起跑、无测量读数**）"
                          "⇒ 清场后 ceiling 2888 / prev_swing 125 / margin 125 / REQ 2775 开窗"),
            "mechanism": ("J0 PASS（面集合 ['candidates'] ∧ C 档五字段缺席 9/9 ∧ 前缀同源 25c97bef… ∧ 跨轮锚成立）；"
                          "J1（主）PASS：面=candidates 9/9 ∧ executed>0 9/9 ∧ 守恒违例 0 ∧ unmapped 0 / 期望继承 39；"
                          "**J1d PASS（candidates ∧ executed==0 形态 0/9）**；**J1e=NOT_EXERCISED（plan_fallback 0/9）**；"
                          "J2b PASS；J2 T_converged 3 vs C 2（继承面不达）"),
            "quality_secondary": ("整题全对 T 3/3·0/3·3/3（池化 6/9=0.6667，Wilson95 [0.3542,0.8794]，用例中位 58）"
                                  "vs C 2/3·2/3·1/3（5/9=0.5556，[0.2666,0.8112]）vs C1 真值 1/1·1/1·1/1（3/3=1.0000）；"
                                  "逐窗配对差 T−C +0.3333/−0.6667/+0.6667（极差 1.333）；J5 与 R617 同号"
                                  "（池化 +0.1111 vs +0.3334 ⇒ pass）但摆动≫效应 ⇒ 非承重；任务面 v3 PASS（D_list [0,−4,0]，中位 0，有效窗 3）"),
            "cost_ref_unacceptable": ("铁律 11 rc=1 ⇒ 参考(未可验收)：调用 Σ T 18 vs C 19；新算 prompt Σ T 14,877 vs C 13,981；"
                                      "**单位调用新算 826.5 vs 735.84（T 更差 ⇒ J3v2 FAIL: a2_per_window_calls:w212 ∧ b1_unit_new_prompt）**；"
                                      "completion Σ T 70,366 vs C 65,970；命中率（中继 dump 时间轴口径）v_all T 0.8838–0.9709 / C 0.8947–0.9709，"
                                      "v_incr T 0.8121–0.9097（8/9 上报）/ C 0.8305–0.9339（7/9 上报）；未上报条数**单列不按 0 计入**"),
            "steps": ("steps_executed 中位 T 6（plan_steps_total 中位 12）/ C 7（plan 中位 10）；rc 分布 T {5:6, 0:3}"
                      "（expect_stdout_exhausted ×5 / run_rc_exhausted ×1）/ C {5:6, 4:1, 0:2}"),
            "failure_modes": ("U1 **回退分支零行使**（plan_fallback 0/9）——9/9 治疗档均映射出非空执行面 ⇒ 回退前提从未成立 ⇒ "
                              "机制**未测到**（不作有效/无效结论）；U2 rc=5 六例（expect_stdout_exhausted ×5）与 R618 同族、**未定因**、本轮不修；"
                              "U3 能力面 w212 T 0/3 属单窗摆动（同臂跨窗 3/3→0/3→3/3），禁单窗结论"),
            "ironlaw11": ("exec_precondition.py --round r619 rc=1（21 臂独立物化实跑）：executable_and_correct=false，"
                          "blocked 全局 7 / 验收面 28（UNDECLARED_SCOPE），实质为用例级失败（如 w211/agentC-r3 51/58 failed=wythoff#43..#54）；"
                          "**首跑 BLOCKED=missing_case_script ×21 系假阻断**（本轮缺 cases/ 字节同源副本，runner 取正本 r610）"
                          "⇒ 逐字节补齐（d9aecf4d397550b8 / 270128eb85c7afc0）后**只重跑后处理**（零重测），"
                          "原读数保留 precond-r619.layout-gap.json"),
            "instrument_defects": ("I1 读取契约缺本轮新键（影子自检 F 态当场抓到 → 两处并入后 8 态全绿，未产生最终假红）；"
                                   "I2 铁律 11 证据布局缺 cases/（假阻断）⇒ 补齐后只重跑后处理；"
                                   "I3 起手闸首试 fail-closed（ceiling 2687，差额 37MB）⇒ 清场重派生，未降门槛"),
        },
        # 引用的 baselines id 逐条对齐 eval/capability/baselines.json 现有条目（RF0004 §4.1 引用义务）
        "baselines": ["F_env.prefix.chars", "F_env.prefix.sha256", "F_env.prefix.r615_anchor",
                      "F_env.gate.prev_swing_mb", "F_env.gate.ceiling_mb",
                      "F_merge.quality.allpass", "F_merge.quality.cases_median_truth",
                      "F_merge.cache.hit_v_all", "F_merge.cost.new_prompt_sum", "F_orch.cost.calls_sum",
                      "F_merge.gate.precondition_rc"],
        "prereg": "eval/rover/r619/prereg-r619.json",
        "evidence": "eval/rover/r619/report-r619.md",
        "verdict": "eval/rover/r619/verdict-r619.json",
    }
    with io.open(KPI, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    lines = [l for l in io.open(KPI, encoding="utf-8").read().splitlines() if l.strip()]
    last = json.loads(lines[-1])
    print("KPI_APPEND=OK lines=%d last_round=%s baselines=%d"
          % (len(lines), last["round"], len(last["baselines"])))
    return 0


if __name__ == "__main__":
    rc = registry_add()
    if rc:
        raise SystemExit(rc)
    raise SystemExit(kpi_add())
