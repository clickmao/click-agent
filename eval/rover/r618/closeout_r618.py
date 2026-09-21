#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R618 收口: 登记表新增行 + kpi 行追加（程序化改写纪律: 先断言序列化器逐字节复现原文件）。"""
import hashlib
import io
import json
import os
import sys

ROOT = "/home/agentuser/AgentFramework"
REG = os.path.join(ROOT, "docs/verification-registry.json")
KPI = os.path.join(ROOT, "eval/capability/kpi.jsonl")


def sha12(p):
    return hashlib.sha256(io.open(os.path.join(ROOT, p), "rb").read()).hexdigest()[:12]


def registry_add():
    raw = io.open(REG, encoding="utf-8").read()
    doc = json.loads(raw)
    if json.dumps(doc, indent=1, ensure_ascii=False) + "\n" != raw:
        print("SER_ASSERT=FAIL ⇒ 拒绝写盘 (fail-closed)")
        return 3
    print("SER_ASSERT=OK (indent=1/ensure_ascii=False/tail=LF)")
    rid = "r618.exec-face-wiring"
    if any(r.get("id") == rid for r in doc["rows"]):
        print("ROW_EXISTS ⇒ 幂等跳过")
        return 0
    art = sha12("eval/rover/r618/report-r618.md")
    inst = sha12("eval/rover/r618/judge_r618.py")
    row = {
        "id": rid,
        "capability": (
            "RF0004.2 · M3 **第二刀 = 执行面接线**：把 R610 第一刀产出的 `accepted` 采纳集接到执行面"
            "（窄腰 `write_file`/`run_command`），使「执行什么」与「声明什么」同源。真机（w208..w210，21 跑次，"
            "被测件 sha256 `886db888d744a6196dbdefd6aa482c8fc0b966eaab16fac7e6c3add44a0f3ca6`，`bin_sha_stable=true`）："
            "① **J0 臂轴生效 PASS** —— T 档 `exec_source=candidates` **9/9** vs C 档四新字段**全缺席 9/9**"
            "（轴关 = 旧行为逐字节同），两臂前缀 `prefix_sha256` 均为 `25c97bef…`（= R617 pin 逐位 ⇒ r1gen 零改动，跨轮锚成立）；"
            "② **J1（主判据）PASS** —— 有 `executed>0` 跑次 **8/9**、四字段齐备 8/9、**守恒违例 0**"
            "（`unmapped<=accepted ∧ executed<=accepted−unmapped ∧ inherited<=accepted−unmapped`），"
            "`unmapped` 合计 0 / 自述期望继承合计 26 ⇒ 换载体未丢自检面；③ J2b PASS（8/9 跑次 accepted+rejected==declared，违例 0）；"
            "④ **能力面负向**：整题全对 T **4/9=0.444** vs C **6/9=0.667** vs codex 真值 2/3，逐窗配对差 +0.333/−0.667/−0.333 ⇒ "
            "**J5 跨窗集方向不一致**（R617 +0.3334 vs 本轮 −0.2223）⇒ 该轴在能力面**非承重、不构成提升**；"
            "⑤ J3 v2 FAIL（`a2_per_window_calls:w209` ∧ `b1_unit_new_prompt`），J3 v1 PASS；"
            "⑥ **铁律 11 rc=1（未可验收）**：blocked 9 臂（T 5 / C 3 / codex 1），含两枚 0/58（`w209/agentT-r1` 探针未达成、"
            "`w210/agentT-r1` 零步执行面）⇒ 一切质量/成本读数标「参考（未可验收）」。"
            "**只证「执行面被采纳集驱动 + 条目守恒」；不证能力或成本收益，且实测为负向。**"),
        "level": "L3",
        "evidence_cmd": (
            "bash eval/rover/r618/run_r618.sh   # 21 跑次（T×9 / C×9 / C1×3），落 $HOME/.agentframework/harness/runs/r618/；"
            "判据器影子自检: python3 eval/rover/r618/selftest_judge_r618.py（5 态）；"
            "后处理重算: python3 eval/rover/r618/judge_r618.py --D $HOME/.agentframework/harness/runs/r618 --pd eval/rover/r618；"
            "AOT: bash eval/rover/r618/aot_r618.sh；铁律 11: python3 eval/rover/r507pre/exec_precondition.py --round r618"),
        "evidence_path": "eval/rover/r618/report-r618.md",
        "negative_control": (
            "① **判据器影子自检五态**（`eval/rover/r618/selftest_judge_r618.py`，合成台账，rc=0 全态符合）："
            "正常 / **两臂不可区分**（C 档也带四字段 ⇒ J0 判红 + defects 点名） / **真空**（T 档四字段全缺席 ⇒ J1 fail-closed"
            "不可判、`vacuous_reason=VACUOUS`） / **守恒违例**（`executed>accepted−unmapped` ⇒ J1b 判红且非真空） / "
            "**跨轮锚不成立**（两臂同源但与 R617 pin 不同 ⇒ J0 仍 True、只记 `claims_violated`，钉住「判据面 vs 宣称面」分离）；"
            "② **同轮轴关负控**：C 档（`AGENTFRAMEWORK_R1_ACTION_EXEC` unset）逐跑次四字段缺席 9/9 ⇒ 「轴关 = 旧行为」"
            "由机检而非叙述保证；③ **单测零回归条**：`ActionExecPlanTests.零回归`（轴关时执行面与 `sem.Plan` 逐位相等 + "
            "台账字段不出现）＋映射守恒条（坏参数/窄腰外工具计 `unmapped`、不静默丢）；"
            "④ **铁律 11 fail-closed**：blocked 非空 ⇒ rc=1（不得 rc=0 假绿）。"),
        "covers": ["eval/rover/r618/dag-r618.md", "eval/rover/r618/prereg-r618.json",
                   "eval/rover/r618/report-r618.md", "eval/rover/r618/run_r618.sh",
                   "eval/rover/r618/judge_r618.py", "eval/rover/r618/selftest_judge_r618.py",
                   "eval/rover/r618/aot_r618.sh", "eval/rover/r618/repin_api_r618.sh",
                   "eval/rover/r618/taskset-r618.json", "eval/rover/r618/bins-r618.json",
                   "eval/rover/r618/gate-margin-r618.json", "eval/rover/r618/kpi-table-r618.json",
                   "eval/rover/r618/verdict-r618.json", "eval/rover/r618/cases/run_cases_r521.py",
                   "eval/rover/r618/cases/cases-r521.json",
                   "src/agent/r1/ActionExecPlan.cs", "src/agent/r1/AcceptedAction.cs",
                   "src/agent/r1/ActionCandidates.cs", "src/agent/r1/R1Pipeline.cs",
                   "src/agent/r1/R1Transcript.cs", "src/agent/r1/R1RunResult.cs",
                   "src/agent.tests/ActionExecPlanTests.cs"],
        "owner_round": "R618",
        "updated_round": "R618",
        "note": ("轴**默认 off、未放行**（关闭态由逐跑次字段缺席 + 单测逐位双钉）；第二刀只接动作面，信息类工具"
                 "（read_file/list_dir/delete_file）属第三刀；能力面负向的两个可机检来源 = 无候选⇒空执行面（1/9 跑次）"
                 "与早退更早（6/9 跑次 executed=6<mapped），**未定因**（候选序 vs plan 序差异未证，禁无证据归因）；"
                 "M3 出口闸（调用数去重 ≤ 旧臂 50%）本轮只作读数不作验收（分母形态不同源）。"),
        "evidence_generated_with": {
            "evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
            "artifact_sha12": art, "instrument": "eval/rover/r618/judge_r618.py",
            "instrument_sha12": inst, "binding": "audit-pin", "audited_by_round": "R618"},
    }
    doc["rows"].append(row)
    doc["updated_round"] = "R618"
    io.open(REG, "w", encoding="utf-8").write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    back = json.loads(io.open(REG, encoding="utf-8").read())
    assert back["rows"][-1]["id"] == rid and back["updated_round"] == "R618"
    print("REGISTRY_ADD=OK rows=%d new_id=%s artifact_sha12=%s instrument_sha12=%s"
          % (len(back["rows"]), rid, art, inst))
    return 0


def kpi_add():
    row = {
        "round": "R618",
        "ts": "2026-09-21T17:28:49+08:00",
        "kind": ("RF0004.2 · M3 第二刀 = 执行面接线 真机臂 w208..w210（21 跑次）：机制面 **PASS**"
                 "（T 档 exec_source=candidates 9/9 ∧ 守恒违例 0 ∧ 两臂可区分 ∧ 前缀与 R617 pin 逐位同）、"
                 "能力面 **负向**（整题全对 T 4/9 vs C 6/9 vs 真值 2/3，逐窗 +0.33/−0.67/−0.33 翻号，J5 不一致）、"
                 "成本面 J3v2 FAIL、铁律 11 rc=1 ⇒ 一切读数**参考（未可验收）**"),
        "change": ("产品侧最小改动 + 器具：① 新记录 `AcceptedAction`（id/工具/args 原文/理由）作采纳集载体，"
                   "`ActionCandidates.Selection` 增 `AcceptedActions`；② 新映射器 `ActionExecPlan`（窄腰 write_file/run，"
                   "同源 `ActionToolDecl`，窄腰外工具计 unmapped，自述期望由 plan 里 (工具,参数) 逐字命中节点**继承**）；"
                   "③ 唯一接线点 `R1Pipeline.cs`（`execPlan = map.Steps` 取代 `sem.Plan`；轴关 ⇒ `execPlan == sem.Plan` 逐位等价）；"
                   "④ 台账四字段 `exec_source/_executed/_unmapped/_expect_inherited`（轴关 ⇒ 缺席）；"
                   "⑤ 单测 `ActionExecPlanTests` 9 条；⑥ 判据器 `eval/rover/r618/judge_r618.py`（J0/J1 重写 + 读取契约并入新键）"
                   "+ 影子自检 5 态。**前缀零改动**：r1gen 未动 ⇒ T/C 两档 prefix_sha256 均 25c97bef…（= R617 pin）；"
                   "API 基线重钉 20 行（全属本轮新增成员）"),
        "readings": {
            "real_arms": ("21 跑次（T×9 / C×9 / C1×3）；窗集 w208..w210（与历史 w184..w207 不相交）；"
                          "被测件 sha256 886db888d744a6196dbdefd6aa482c8fc0b966eaab16fac7e6c3add44a0f3ca6（19,834,064 B）"
                          "∧ bin_sha_stable=true；题集 sha16 e0c667c2a313c04b"),
            "mechanism": ("J0 PASS（T exec_source=candidates 9/9 ∧ C 四字段缺席 9/9 ∧ 两臂前缀同源 25c97bef… ∧ "
                          "跨轮锚成立 claims_violated=[]）；J1（主）PASS：executed>0 8/9 ∧ 四字段齐备 8/9 ∧ 守恒违例 0 ∧ "
                          "unmapped 合计 0 / 期望继承合计 26；J2b PASS（8/9 跑次 accepted+rejected==declared，违例 0）"),
            "quality_negative": ("整题全对 T 4/9=0.4444（Wilson95 [0.189,0.733]；逐窗 3/3·1/3·0/3，用例中位 49）"
                                 "vs C 6/9=0.6667（[0.354,0.879]；2/3·3/3·1/3，中位 58）vs C1 真值 2/3（w208 52/58 自败）；"
                                 "逐窗配对差 T−C +0.333/−0.667/−0.333；J5 方向与 R617 相反（+0.3334 → −0.2223）⇒ 非承重；"
                                 "任务面 v3：有效窗 2（w208 剔出，单列我方 58）label 不达（D_list [−11,−15]，中位 −13）"),
            "cost_ref_unacceptable": ("铁律 11 rc=1 ⇒ 参考(未可验收)：调用 Σ T 16 vs C 16；新算 prompt Σ 12,138 vs 12,054；"
                                      "**单位调用新算 758.6 vs 753.4（b1 更差 ⇒ J3v2 FAIL）**；completion Σ 59,803 vs 58,603（+2.0%）；"
                                      "命中率（中继 dump 时间轴口径）v_all 0.9035–0.9709 vs 0.9071–0.9709；bad_dumps 0"),
            "steps": ("steps_executed 中位 T 6 / C 15（plan_steps_total 中位 T 10 / C 10）；repair_rounds 全 0；"
                      "rc 分布 T：rc=5 ×5 / rc=0 ×2 / rc=8 ×1 / rc=0(零步 ready) ×1；C：rc=0 ×5 / rc=5 ×4"),
            "failure_modes": ("D1 无候选 ⇒ 空执行面 ⇒ 零步执行（w210/agentT-r1：declared/accepted 缺席 ∧ executed=0 ∧ "
                              "plan_steps_total=10）= 轴引入的新失败形态；D2 早退更早（6/9 T 跑次 executed=6<mapped，"
                              "w210/agentT-r2 reason=step a7 stdout 与 expect_stdout 不符）**未定因**；D3 rc=8 产物未成型（既有族）"),
            "ironlaw11": ("exec_precondition.py --round r618 rc=1（21 臂独立物化实跑；blocked 9 = T 5 / C 3 / codex 1；"
                          "含 w209/agentT-r1 与 w210/agentT-r1 各 0/58，codex w208 52/58；首跑 BLOCKED=missing_case_script ⇒ "
                          "从 r610 逐字节补齐 eval/rover/r618/cases/（d9aecf4d397550b8 / 270128eb85c7afc0）后**只重跑后处理**）"),
            "instrument_defects": ("I1 判据器首跑前发现读取契约缺本轮新键（承 R617 自捕教训）⇒ 建判据器时即并入 TR_FIELDS，"
                                   "未产生假红；I2 铁律 11 missing_case_script（器具面缺 cases/）⇒ 逐字节补齐后重跑后处理，"
                                   "不重测；I3 起手闸 cap_binding=true（振幅项退化 125→104MB）已落盘登记"),
        },
        # 引用的 baselines id 逐条对齐 eval/capability/baselines.json 现有条目（RF0004 §4.1 引用义务）
        "baselines": ["F_env.prefix.chars", "F_env.prefix.sha256", "F_env.prefix.r615_anchor",
                      "F_env.gate.prev_swing_mb", "F_env.gate.ceiling_mb",
                      "F_merge.quality.allpass", "F_merge.quality.cases_median_truth",
                      "F_merge.cache.hit_v_all", "F_merge.cost.new_prompt_sum", "F_orch.cost.calls_sum",
                      "F_merge.gate.precondition_rc"],
        "prereg": "eval/rover/r618/prereg-r618.json",
        "evidence": "eval/rover/r618/report-r618.md",
        "verdict": "eval/rover/r618/verdict-r618.json",
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
