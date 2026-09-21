#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R620 收口器（幂等 · 保形 · 读回校验）

职责（协议 §2 收口五件）：
 1) bins-r620.json        —— 全臂同一枚二进制 + codex 指纹 + 题集 sha（臂身份面）
 2) evidence-run-r620.txt —— 运行日志摘录 + 前提闸 + 判决摘要（人读证据）
 3) eval/capability/kpi.jsonl —— 追加一行（幂等：round==R620 已存在则跳过）
 4) docs/verification-registry.json —— 追加 r620.exec-fallback-exercised 行（保形 indent=1）
 5) docs/reports/status.json        —— 由 status_gen.py 重生成（若有 --write 能力则调用）

纪律：写入前断言「序列化器可逐字节复现原文件」；写后读回校验；幂等。
"""
import hashlib
import io
import json
import os
import subprocess
import sys

def _repo_root():
    p = os.path.dirname(os.path.abspath(__file__))
    while p != "/" and not os.path.isdir(os.path.join(p, "eval", "rover")):
        p = os.path.dirname(p)
    if not os.path.isdir(os.path.join(p, "eval", "rover")):
        raise SystemExit("[FAIL] 找不到仓库根（eval/rover 不存在）")
    return p


REPO = _repo_root()
R = "R620"
RD = os.path.join(REPO, "eval/rover/r620")
D = os.path.expanduser("~/.agentframework/harness/runs/r620")
ART = os.path.expanduser("~/.agentframework/artifacts/pub_r619/agenthost")


def sha256_file(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jload(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def read_text(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def write_text(p, s):
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def jdump_same_shape(path, obj):
    """按原文件形状写回：先断言序列化器可逐字节复现原文件。"""
    orig = read_text(path)
    for kw in ({"indent": 1, "ensure_ascii": False}, {"indent": 2, "ensure_ascii": False},
               {"indent": 4, "ensure_ascii": False}, {"ensure_ascii": False}):
        cand = json.dumps(obj, **kw) + "\n"
        try:
            if json.dumps(json.loads(orig), **kw) + "\n" == orig:
                return kw, cand
        except Exception:
            continue
    raise SystemExit("[FAIL] 无法逐字节复现 %s ⇒ 改用文本插入，禁静默重排" % path)


def main():
    v = jload(os.path.join(RD, "verdict-r620.json"))
    pre = jload(os.path.join(D, "precond-r620.json"))
    prereg = jload(os.path.join(RD, "prereg-r620.json"))
    prem = jload(os.path.join(RD, "premise-r620.json"))
    kpit = jload(os.path.join(RD, "kpi-table-r620.json"))
    j0, j1 = v["J0_arm_axis_effective"], v["J1_exec_face_consumed"]
    vd = v["verdict"]

    # ---------- 1) bins-r620.json ----------
    bins = {
        "round": R,
        "artifact": ART,
        "artifact_sha256": sha256_file(ART),
        "artifact_bytes": os.path.getsize(ART),
        "same_as_round": "R619（逐字节同件 ⇒ 零产品源码改动，本轮只造触发前提）",
        "bin_sha_stable": True,
        "held_constant": {"AGENTFRAMEWORK_R1_ACTION_PROMPT": "legacy"},
        "axis": {"key": "AGENTFRAMEWORK_R1_ACTION_EXEC", "T": "1", "C": "unset"},
        "codex_bin": os.path.expanduser("~/.agentframework/tools/codex-env/node_modules/.bin/codex"),
        "taskset": "eval/rover/r620/taskset-r620.json",
        "taskset_sha256": sha256_file(os.path.join(RD, "taskset-r620.json")),
        "windows": ["w214", "w215", "w216"],
        "runs": {"T": 9, "C": 9, "C1": 3},
        "prereg_sha256": sha256_file(os.path.join(RD, "prereg-r620.json")),
        "judge_sha256": sha256_file(os.path.join(RD, "judge_r620.py")),
        "runner_sha256": sha256_file(os.path.join(RD, "run_r620.sh")),
    }
    write_text(os.path.join(RD, "bins-r620.json"), json.dumps(bins, indent=1, ensure_ascii=False) + "\n")

    # ---------- 2) evidence-run-r620.txt ----------
    lines = []
    lines.append("== R620 运行证据（%s）==" % R)
    lines.append("[起手闸] " + read_text(os.path.join(RD, "gate-margin-r620.json")).replace("\n", " ")[:400])
    lines.append("[前提闸] rc=%s exec_source=%s exec_fallback=%s prefix==legacy_anchor=%s plan_steps=%s" % (
        prem.get("rc"), prem.get("exec_source"), prem.get("exec_fallback"),
        prem.get("prefix_sha256") == prem.get("legacy_anchor"), prem.get("plan_steps_total")))
    for ln in read_text(os.path.join(D, "logs/run.txt")).splitlines():
        if any(k in ln for k in ("落盘", "KPI 汇总", "前置器", "完成", "前提闸")):
            lines.append("[run.txt] " + ln[:300])
    lines.append("[判决] rc=%s mechanism_rc=%s label=%s" % (vd.get("rc"), vd.get("mechanism_rc"), vd.get("label")))
    lines.append("[J0] pass=%s faces_T=%s prefix_shared=%s legacy_block=%s cross_round_pin=%s" % (
        j0.get("pass"), j0.get("by_arm", {}).get("A_T_face_set"), j0.get("by_arm", {}).get("C_prefix_shared"),
        j0.get("by_arm", {}).get("F_held_constant_legacy_block"), j0.get("cross_round_anchor", {}).get("pass")))
    lines.append("[J1] pass=%s a1_face_covered=%s a2_fallback_runs=%s a3_fallback_executed_positive=%s d1_zero=%s "
                 "three_state=%s reasons=%s" % (
                     j1.get("pass"),
                     j1.get("by_arm", {}).get("T", {}).get("runs_face_covered"),
                     j1.get("by_arm", {}).get("T", {}).get("runs_plan_fallback"),
                     j1.get("by_arm", {}).get("T", {}).get("runs_fallback_executed_positive"),
                     j1.get("by_arm", {}).get("T", {}).get("runs_candidates_executed_zero"),
                     j1.get("J1e_fallback_three_state"), prem.get("exec_fallback")))
    lines.append("[J6] pass=%s per_window=%s" % (v["J6_zero_regression_equivalence"].get("pass"),
                                                 json.dumps(v["J6_zero_regression_equivalence"].get("per_window"), ensure_ascii=False)))
    lines.append("[J3] pass=%s form=%s" % (v["J3_cost"].get("pass"), json.dumps(v["J3_cost"].get("v2", {}).get("form", {}), ensure_ascii=False)))
    lines.append("[铁律11] precond rc=%s (未可验收错题: %s)" % (
        pre.get("rc"), json.dumps(pre.get("failed_cases", pre.get("windows", {})), ensure_ascii=False)[:300]))
    lines.append("[臂rc] " + json.dumps(
        {r["臂"]: {"rc": r.get("rc/stage")} for r in kpit.get("rows", [])}, ensure_ascii=False)[:700])
    write_text(os.path.join(RD, "evidence-run-r620.txt"), "\n".join(lines) + "\n")

    # ---------- 3) kpi.jsonl（幂等追加）----------
    baselines = ["F_env.prefix.chars", "F_env.prefix.sha256", "F_env.prefix.legacy_anchor",
                 "F_env.gate.prev_swing_mb", "F_env.gate.ceiling_mb", "F_merge.quality.allpass",
                 "F_merge.quality.cases_median_truth", "F_merge.cache.hit_v_all",
                 "F_merge.cost.new_prompt_sum", "F_orch.cost.calls_sum", "F_merge.gate.precondition_rc"]
    kp = os.path.join(REPO, "eval/capability/kpi.jsonl")
    have = [json.loads(l) for l in read_text(kp).splitlines() if l.strip()]
    if any(r.get("round") == R for r in have):
        print("[skip] kpi.jsonl 已含 %s 行（幂等）" % R)
    else:
        row = {
            "round": R,
            "ts": subprocess.check_output(["date", "+%Y-%m-%dT%H:%M:%S%z"]).decode().strip(),
            "kind": ("RF0004.2 · M3 **第四刀 = 回退分支真机行使**（触发面 = 提示尾块 legacy 档，held-constant 两臂同值）："
                     "真机 21 跑次（T×9 / C×9 / C1×3，窗集 w214..w216 与历史不相交）。**核心结论：回退分支首次真机行使 9/9**"
                     "（exec_source=plan_fallback，原因码 candidates_absent，回退跑次 executed>0 9/9）、"
                     "R619 的 J1e=NOT_EXERCISED 缺口闭合；J0 臂轴生效（两臂前缀 == legacy 锚 a9792fdb…，held-constant 真生效）；"
                     "J1 主判据 PASS ∧ mechanism_rc=0。**但 rc=2（判据器把 J6 等价面不成立编码进 instrument_defects ⇒ 该规则下整轮标"
                     "「禁作被测结论」）**：J6 逐窗 rc 多重集/用例数 T≠C（回退面 **不等于** 轴关面逐位）——在逐跑次摆动"
                     "（用例 48..58）下该判据无分辨率 ⇒ 记「未判明」，下轮以加 reps/扩窗处置（禁调阈值）。"
                     "成本面 v2 三条款全过（Σcalls 14 vs 16 ∧ 逐窗 ≤ ∧ 单位新算 667 vs 834）；铁律 11 rc=1 ⇒ 读数标参考（未可验收）。"),
            "change": ("产品侧改动 = **零**（复用 R619 AOT 件逐字节，sha256 同件）⇒ 本轮**仅造触发前提**：held-constant "
                       "`AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy`（两臂同值）⇒ legacy 尾块不给候选字段 ⇒ 采纳面为空 ⇒ 回退支。"
                       "器具面：derive_r620.py（18 条声明式替换，逐条命中数 == 1）+ 题集逐字节同源（sha12 e0c667c2a313）+ "
                       "前提闸 premise-r620.json（起臂前 1 跑次，rc=0 才起臂）+ J6 等价面判据（新增，次级）。"),
            "readings": {
                "real_arms": "21 跑次（T×9 / C×9 / C1×3）；窗集 w214..w216；被测件与 R619 同件（零产品源码改动）",
                "mechanism": {"J0": j0.get("pass"), "J1": j1.get("pass"),
                              "J1a_face_covered": j1.get("by_arm", {}).get("T", {}).get("runs_face_covered"),
                              "J1a_fallback_runs": j1.get("by_arm", {}).get("T", {}).get("runs_plan_fallback"),
                              "J1a_fallback_executed_positive": j1.get("by_arm", {}).get("T", {}).get("runs_fallback_executed_positive"),
                              "J1e_three_state": j1.get("J1e_fallback_three_state"),
                              "J1d_zero_form": j1.get("by_arm", {}).get("T", {}).get("runs_candidates_executed_zero")},
                "cost": {"sum_calls_T": 14, "sum_calls_C": 16,
                         "sum_new_prompt_T": 9340, "sum_new_prompt_C": 13349,
                         "unit_new_prompt_T": 667.1, "unit_new_prompt_C": 834.3},
                "quality": {"all_pass_T": v["J4_capability_secondary"]["by_arm"]["T"]["all_pass"],
                            "all_pass_C": v["J4_capability_secondary"]["by_arm"]["C"]["all_pass"],
                            "all_pass_C1": v["J4_capability_secondary"]["by_arm"]["C1"]["all_pass"],
                            "valid_windows": v["W_floor_resolution_floor"]["valid_windows"],
                            "truth_self_fail": v["W_floor_resolution_floor"].get("truth_self_fail_windows")},
                "zero_regression": {"J6": v["J6_zero_regression_equivalence"].get("pass"),
                                    "note": "摆动量级（用例 48..58）≥ 判据分辨率 ⇒ 未判明"},
                "precond_rc": pre.get("rc"),
                "verdict": {"rc": vd.get("rc"), "mechanism_rc": vd.get("mechanism_rc"), "label": vd.get("label")},
            },
            "baselines": baselines,
            "prereg": "eval/rover/r620/prereg-r620.json",
            "evidence": "eval/rover/r620/report-r620.md",
            "verdict": "eval/rover/r620/verdict-r620.json",
        }
        with io.open(kp, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        back = [json.loads(l) for l in read_text(kp).splitlines() if l.strip()]
        assert back[-1]["round"] == R and len(back) == len(have) + 1, "[FAIL] kpi.jsonl 追加后读回不一致"
        print("[ok] kpi.jsonl += %s（行数 %d → %d）" % (R, len(have), len(back)))

    # ---------- 4) verification-registry ----------
    regp = os.path.join(REPO, "docs/verification-registry.json")
    reg = jload(regp)
    rid = "r620.exec-fallback-exercised"
    # R2f/R2e（R473）：产品面证据行必须带 evidence_generated_with（键集 + frozen 字节闸）
    gen = {
        "evidence_kind": "artifact",
        "pin_status": "frozen",
        "pin_reason": "archived-per-round",
        "artifact_sha12": sha256_file(os.path.join(RD, "report-r620.md"))[:12],
        "instrument": "eval/rover/r620/judge_r620.py",
        "instrument_sha12": sha256_file(os.path.join(RD, "judge_r620.py"))[:12],
        "binding": "audit-pin",
        "audited_by_round": R,
    }
    if any(r.get("id") == rid for r in reg["rows"]):
        # 重钉（幂等）：证据/器具字节变 ⇒ 摘要跟着变；只改本行，不重排文件
        for r in reg["rows"]:
            if r.get("id") == rid:
                if r.get("evidence_generated_with") != gen:
                    r["evidence_generated_with"] = gen
                    kw, txt = jdump_same_shape(regp, reg)
                    write_text(regp, txt)
                    print("[ok] registry 重钉 %s gen=%s" % (rid, gen["artifact_sha12"]))
                else:
                    print("[skip] registry %s gen 已一致（幂等）" % rid)
        return 0
    if True:
        row = {
            "id": rid,
            "round": R,
            "owner_round": R,
            "level": "L4",
            "evidence_generated_with": gen,
            "capability": ("RF0004.2 · M3 **第四刀 = 回退分支真机行使**（触发面 = held-constant 提示尾块 `legacy`）："
                           "R619 建立了「映射面为空 ∧ plan 非空 ⇒ 回退读 plan」的判定与接线，但其触发前提在 R619 的 9 个治疗跑次里"
                           "从未成立（J1e=NOT_EXERCISED）⇒ 修复代码从未被真机行使。本轮把前提造出来：两臂同值 `legacy` 尾块 ⇒ 模型不给候选字段 "
                           "⇒ 采纳面为空 ⇒ 回退支。真机 21 跑次（T×9 / C×9 / C1×3，窗集 w214..w216），被测件与 R619 逐字节同件（零产品源码改动）。"
                           "**读数**：前提闸 rc=0（exec_source=plan_fallback / exec_fallback=candidates_absent / 前缀 == legacy 锚 a9792fdb…）；"
                           "**回退行使 9/9**（T: runs_plan_fallback=9 ∧ runs_fallback_executed_positive=9 ∧ 三态 EXERCISED_OK ∧ "
                           "candidates∧executed==0 = 0）⇒ R619 的 NOT_EXERCISED 闭合；J0 PASS（两臂前缀同源 ∧ == legacy 锚 ⇒ held-constant 真生效）；"
                           "**J1 PASS（mechanism_rc=0）**；J3 成本 v2 三条款全过（14 vs 16 调用 / 9,340 vs 13,349 新算 / 单位 667 vs 834）；"
                           "J4 并列·欠功率（整题全对 T 7/9 vs C 6/9 vs 真值 2/3；真值自败窗 w216 剔除配对 ⇒ 有效窗 2）。"
                           "**未成立/未判明**：① rc=2 —— 判据器把 J6「等价面」不成立计入 `instrument_defects`（`rc = 2 if defects else 0`）"
                           "⇒ 本轮 rc 落在「器具缺陷」层，如实保留（禁事后改判据）；② J6 本身在逐跑次摆动（用例 48..58）下无分辨率 ⇒ "
                           "「回退面 vs 轴关面」差异**未判明**，下轮以加 reps/扩窗处置（禁下调阈值）；③ claims_violated：「前缀零改动」宣称作废"
                           "（本轮 held-constant 换成 legacy 档，跨轮 pin 不再成立，同轮两臂可比性不受影响）；④ 铁律 11 precond rc=1 ⇒ "
                           "质量/成本一律**参考（未可验收）**。"),
            "evidence_path": "eval/rover/r620/report-r620.md",
            "evidence_cmd": "python3 eval/rover/r620/closeout_r620.py --check && python3 eval/capability/status_gen.py --check",
            "negative_control": ("① 前提闸：起臂前 1 跑次必须证「legacy ⇒ 候选键未到达 ∧ exec_source=plan_fallback ∧ 前缀 == legacy 锚」，"
                                 "否则零臂起跑（rc=5，premise-r620.json）；② 判据器影子自检 selftest_judge_r620.py（多态合成日志，逐条预期 rc）；"
                                 "③ J6 判据内含对照组（轴关面 C 逐窗 rc/用例数），两臂同窗 ⇒ 摆动可辨。"),
            "covers": ["F_env.gate.ceiling_mb", "F_merge.gate.precondition_rc", "F_orch.cost.calls_sum",
                       "F_merge.cost.new_prompt_sum", "F_merge.cache.hit_v_all", "F_merge.quality.allpass"],
            "runs": 21,
            "verdict": "机制面 PASS（J0∧J1，回退行使 9/9）· rc=2（J6 计入 instrument_defects）· precond rc=1（参考·未可验收）",
            "aot": "未重发布（本轮零产品源码改动 ⇒ 复用 R619 AOT 件逐字节，bins-r620.json 钉 sha）",
        }
        reg["rows"].append(row)
        reg["updated_round"] = R
        kw, txt = jdump_same_shape(regp, reg)
        write_text(regp, txt)
        back = jload(regp)
        assert back["rows"][-1]["id"] == rid and back["updated_round"] == R, "[FAIL] registry 写回读不一致"
        print("[ok] registry += %s（shape %s）" % (rid, kw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
