#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R621 收口器（幂等 · 保形 · 读回校验 · --check 只读自检）

来源声明（诚实）：本文件由 **人工适配** 自 `eval/rover/r620/closeout_r620.py`
（R620 的收口器同为人工件；`derive_r620.py`/`derive_r621.py` 只派生
run/judge/selftest/taskset 四件，不含收口器）—— 差异仅在：R621 的 rd/路径/轮号、
rc 分级语义（v4：0/1/2/3）、J6 三态字段（`state` + `delta_median_C_minus_T`）、
以及新增 `--check` 只读分支（使 registry 的 `evidence_cmd` 真实可跑）。

职责（协议 §2 收口五件）：
 1) bins-r621.json        —— 全臂同一枚二进制 + codex 指纹 + 题集 sha（臂身份面）
 2) evidence-run-r621.txt —— 运行日志摘录 + 前提闸 + 判决摘要（人读证据）
 3) eval/capability/kpi.jsonl —— 追加一行（幂等：round==R621 已存在则跳过）
 4) docs/verification-registry.json —— 追加 r621 行（保形 indent=1）
 5) docs/reports/status.json —— 由 status_gen.py 重生成（另行执行）

纪律：写入前断言「序列化器可逐字节复现原文件」；写后读回校验；幂等；
      **禁回溯改 R620 判据**（本轮 rc 列与 R620 不可直接并列，按 mechanism_rc / J6_state 对比）。
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
R = "R621"
RDP = "eval/rover/r621"
RD = os.path.join(REPO, RDP)
D = os.path.expanduser("~/.agentframework/harness/runs/r621")
ART = os.path.expanduser("~/.agentframework/artifacts/pub_r619/agenthost")
WINDOWS = ["w217", "w218", "w219"]
RUNS = {"T": 18, "C": 18, "C1": 3}
RID = "r621.equivalence-resolution-and-rc-tiering"


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


REQUIRED = ["prereg-r621.json", "bins-r621.json", "gate-margin-r621.json",
            "kpi-table-r621.json", "verdict-r621.json", "report-r621.md"]


def check_mode():
    """只读自检（收口五件是否齐 + 判决件是否可解析）—— 零写入。"""
    bad = []
    for f in REQUIRED:
        p = os.path.join(RD, f)
        if not os.path.isfile(p):
            bad.append("缺件: " + RDP + "/" + f)
    if os.path.isfile(os.path.join(D, "logs/run-samples.jsonl")):
        pass
    else:
        bad.append("缺件: " + D + "/logs/run-samples.jsonl")
    rc = 0
    try:
        v = jload(os.path.join(RD, "verdict-r621.json"))
        j6 = v.get("J6_zero_regression_equivalence", {})
        print("[check] verdict rc=%s mechanism_rc=%s J6=%s state=%s" % (
            v.get("verdict", {}).get("rc"), v.get("verdict", {}).get("mechanism_rc"),
            j6.get("pass"), j6.get("state")))
        if j6.get("state") not in ("EQUIVALENT", "NON_REGRESSION_DETECTED", "NO_RESOLUTION",
                                   "DIFFERENCE_FAVOURABLE"):
            bad.append("J6_state 缺省/非法: %r" % j6.get("state"))
            rc = 3
    except Exception as e:
        bad.append("verdict 不可解析: %s" % e)
        rc = 3
    if bad:
        for b in bad:
            print("[check][FAIL] " + b)
        return max(rc, 2)
    print("[check] 收口五件齐备（%d 件）+ 判决件可解析" % len(REQUIRED))
    return 0


def main():
    v = jload(os.path.join(RD, "verdict-r621.json"))
    prereg = jload(os.path.join(RD, "prereg-r621.json"))
    prem = jload(os.path.join(RD, "premise-r621.json"))
    kpit = jload(os.path.join(RD, "kpi-table-r621.json"))
    ppre = os.path.join(D, "precond-r621.json")
    pre = jload(ppre) if os.path.isfile(ppre) else {}
    # precond rc 取法（诚实）：优先取文件自带 rc；否则由验收面字段派生（accept/workable 语义同 R620 前置器 stdout）
    if "rc" not in pre and pre:
        pre["rc"] = 0 if pre.get("acceptable_scoped") else 1
        pre["rc_derived_from"] = "acceptable_scoped（该文件未直接落 rc 字段）"
    j0, j1 = v["J0_arm_axis_effective"], v["J1_exec_face_consumed"]
    j6, j3, j4 = (v["J6_zero_regression_equivalence"], v["J3_cost"],
                  v["J4_capability_secondary"])
    vd = v["verdict"]

    # ---------- 1) bins-r621.json ----------
    bins = {
        "round": R,
        "artifact": ART,
        "artifact_sha256": sha256_file(ART),
        "artifact_bytes": os.path.getsize(ART),
        "same_as_round": "R620（逐字节同件 ⇒ 零产品源码改动；本轮唯一变化 = reps 3→6/窗 + 判据分级）",
        "bin_sha_stable": True,
        "held_constant": {"AGENTFRAMEWORK_R1_ACTION_PROMPT": "legacy"},
        "axis": {"key": "AGENTFRAMEWORK_R1_ACTION_EXEC", "T": "1", "C": "unset"},
        "codex_bin": os.path.expanduser("~/.agentframework/tools/codex-env/node_modules/.bin/codex"),
        "taskset": RDP + "/taskset-r621.json",
        "taskset_sha256": sha256_file(os.path.join(RD, "taskset-r621.json")),
        "windows": WINDOWS,
        "runs": RUNS,
        "prereg_sha256": sha256_file(os.path.join(RD, "prereg-r621.json")),
        "judge_sha256": sha256_file(os.path.join(RD, "judge_r621.py")),
        "runner_sha256": sha256_file(os.path.join(RD, "run_r621.sh")),
        "criterion_version": prereg.get("criterion_version"),
    }
    write_text(os.path.join(RD, "bins-r621.json"),
               json.dumps(bins, indent=1, ensure_ascii=False) + "\n")

    # ---------- 2) evidence-run-r621.txt ----------
    lines = []
    lines.append("== R621 运行证据 ==")
    lines.append("[起手闸] " + read_text(os.path.join(RD, "gate-margin-r621.json")).replace("\n", " ")[:400])
    lines.append("[前提闸] rc=%s exec_source=%s exec_fallback=%s prefix==legacy_anchor=%s plan_steps=%s" % (
        prem.get("rc"), prem.get("exec_source"), prem.get("exec_fallback"),
        prem.get("prefix_sha256") == prem.get("legacy_anchor"), prem.get("plan_steps_total")))
    lr = os.path.join(D, "logs/run.txt")
    if os.path.isfile(lr):
        for ln in read_text(lr).splitlines():
            if any(k in ln for k in ("落盘", "KPI 汇总", "前置器", "完成", "前提闸")):
                lines.append("[run.txt] " + ln[:300])
    lines.append("[判决] rc=%s mechanism_rc=%s label=%s" % (vd.get("rc"), vd.get("mechanism_rc"), vd.get("label")))
    lines.append("[rc分级] " + json.dumps(vd.get("rc_semantics", ""), ensure_ascii=False)[:300])
    lines.append("[J0] pass=%s faces_T=%s prefix_shared=%s legacy_block=%s cross_round_pin=%s" % (
        j0.get("pass"), j0.get("by_arm", {}).get("A_T_face_set"), j0.get("by_arm", {}).get("C_prefix_shared"),
        j0.get("by_arm", {}).get("F_held_constant_legacy_block"),
        j0.get("cross_round_anchor", {}).get("pass")))
    b1 = j1.get("by_arm", {}).get("T", {})
    lines.append("[J1] pass=%s runs_face_covered=%s runs_plan_fallback=%s runs_fallback_executed_positive=%s "
                 "d1_zero=%s three_state=%s" % (
                     j1.get("pass"), b1.get("runs_face_covered"), b1.get("runs_plan_fallback"),
                     b1.get("runs_fallback_executed_positive"), b1.get("runs_candidates_executed_zero"),
                     j1.get("J1e_fallback_three_state")))
    lines.append("[J6 · v4 三态] pass=%s state=%s delta_median_C_minus_T=%s swing=%s per_window=%s" % (
        j6.get("pass"), j6.get("state"), j6.get("delta_median_C_minus_T"), j6.get("swing_mb_or_cases"),
        json.dumps(j6.get("per_window"), ensure_ascii=False)[:400]))
    lines.append("[J6 原始逐窗] " + json.dumps(j6.get("raw_by_window", j6.get("per_window")),
                                              ensure_ascii=False)[:400])
    lines.append("[J3 成本] pass=%s " % j3.get("pass") + json.dumps(j3.get("v2", {}), ensure_ascii=False)[:400])
    lines.append("[J4 质量·并列] T_all_pass=%s C_all_pass=%s C1_all_pass=%s valid_windows=%s truth_self_fail=%s" % (
        j4.get("by_arm", {}).get("T", {}).get("all_pass"), j4.get("by_arm", {}).get("C", {}).get("all_pass"),
        j4.get("by_arm", {}).get("C1", {}).get("all_pass"),
        v.get("W_floor_resolution_floor", {}).get("valid_windows"),
        v.get("W_floor_resolution_floor", {}).get("truth_self_fail_windows")))
    lines.append("[铁律11] precond rc=%s failed=%s" % (
        pre.get("rc"), json.dumps(pre.get("failed_cases", {}), ensure_ascii=False)[:300]))
    lines.append("[器具缺陷] " + json.dumps(v.get("instrument_defects", []), ensure_ascii=False)[:300])
    lines.append("[次级红] " + json.dumps(v.get("mechanism_secondary_failures", []), ensure_ascii=False)[:300])
    lines.append("[臂rc] " + json.dumps(
        {r["臂"]: {"rc": r.get("rc/stage")} for r in kpit.get("rows", [])}, ensure_ascii=False)[:700])
    write_text(os.path.join(RD, "evidence-run-r621.txt"), "\n".join(lines) + "\n")

    # ---------- 3) kpi.jsonl（幂等追加）----------
    baselines = ["F_env.prefix.chars", "F_env.prefix.sha256", "F_env.prefix.legacy_anchor",
                 "F_env.gate.prev_swing_mb", "F_env.gate.ceiling_mb", "F_merge.quality.allpass",
                 "F_merge.quality.cases_median_truth", "F_merge.cache.hit_v_all",
                 "F_merge.cost.new_prompt_sum", "F_orch.cost.calls_sum", "F_merge.gate.precondition_rc"]
    j6st = j6.get("state")
    kind = ("RF0004.2 · M3 **第五刀 = 等价面分辨率取证（reps 3→6/窗）+ 判据分级**："
            "R620 的 J6「回退面 == 轴关面」在逐跑次用例数摆动 48..58 下**无分辨率**，且被编码进 "
            "`instrument_defects` ⇒ 整轮标「禁作被测结论」。本轮只做 R620 登记的两件补救："
            "① 判据分级（v4：J6 移出 instrument_defects ⇒ rc 0/1/2/3 分层）；② reps 3→6/窗。"
            "**零产品源码改动**（复用 pub_r619 逐字节同件，sha a184d731…），唯一变量与 R620 同轴同档位。"
            "真机 %d 跑次（T×%d / C×%d / C1×%d，窗集 %s 与历史不相交）。"
            "读数：J0=%s（两臂前缀 == legacy 锚）· J1=%s（回退行使 %s/%s）· J6=%s（state=%s）· "
            "rc=%s / mechanism_rc=%s · 铁律11 precond rc=%s。" % (
                sum(RUNS.values()), RUNS["T"], RUNS["C"], RUNS["C1"], "..".join([WINDOWS[0], WINDOWS[-1]]),
                j0.get("pass"), j1.get("pass"), b1.get("runs_plan_fallback"), b1.get("runs_face_covered"),
                j6.get("pass"), j6st, vd.get("rc"), vd.get("mechanism_rc"), pre.get("rc", "N/A")))
    change = ("产品侧改动 = **零**（复用 R619 AOT 件逐字节，sha256 同件）⇒ 本轮只动**器具面**："
              "judge_r621.py（v4：J6 三态 + rc 分级 + 判据器头部契约）+ selftest_judge_r621.py"
              "（影子自检 11/11，含「比较变量写反」翻转负控）+ 预注册 v3（先写后跑闸）+ "
              "dag-r621.md（DAG 先行令载体）。**禁回溯改 R620 判据**：R620 的 rc=2 与 J6 不成立照原样保留。")
    row = {
        "round": R,
        "ts": subprocess.check_output(["date", "+%Y-%m-%dT%H:%M:%S%z"]).decode().strip(),
        "kind": kind,
        "change": change,
        "readings": {
            "real_arms": "%d 跑次（T×%d / C×%d / C1×%d）；窗集 %s；被测件与 R619/R620 同件（零产品源码改动）" % (
                sum(RUNS.values()), RUNS["T"], RUNS["C"], RUNS["C1"], "..".join([WINDOWS[0], WINDOWS[-1]])),
            "mechanism": {"J0": j0.get("pass"), "J1": j1.get("pass"),
                          "J1_fallback_runs": b1.get("runs_plan_fallback"),
                          "J1_fallback_executed_positive": b1.get("runs_fallback_executed_positive"),
                          "J1e_three_state": j1.get("J1e_fallback_three_state")},
            "equivalence": {"J6": j6.get("pass"), "state": j6st,
                            "delta_median_C_minus_T": j6.get("delta_median_C_minus_T"),
                            "per_window": j6.get("per_window")},
            "cost": {"v2_pass": j3.get("pass"), "v2": j3.get("v2")},
            "quality": {"all_pass_T": j4.get("by_arm", {}).get("T", {}).get("all_pass"),
                        "all_pass_C": j4.get("by_arm", {}).get("C", {}).get("all_pass"),
                        "all_pass_C1": j4.get("by_arm", {}).get("C1", {}).get("all_pass"),
                        "valid_windows": v.get("W_floor_resolution_floor", {}).get("valid_windows"),
                        "truth_self_fail_windows": v.get("W_floor_resolution_floor", {}).get("truth_self_fail_windows")},
            "precond_rc": pre.get("rc", "N/A"),
            "verdict": {"rc": vd.get("rc"), "mechanism_rc": vd.get("mechanism_rc"), "label": vd.get("label")},
            "instrument_defects": v.get("instrument_defects", []),
            "mechanism_secondary_failures": v.get("mechanism_secondary_failures", []),
        },
        "baselines": baselines,
        "prereg": RDP + "/prereg-r621.json",
        "evidence": RDP + "/report-r621.md",
        "verdict": RDP + "/verdict-r621.json",
    }
    kp = os.path.join(REPO, "eval/capability/kpi.jsonl")
    have = [json.loads(l) for l in read_text(kp).splitlines() if l.strip()]
    if any(r.get("round") == R for r in have):
        print("[skip] kpi.jsonl 已含 %s 行（幂等）" % R)
    else:
        with io.open(kp, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        back = [json.loads(l) for l in read_text(kp).splitlines() if l.strip()]
        assert back[-1]["round"] == R and len(back) == len(have) + 1, "[FAIL] kpi.jsonl 追加后读回不一致"
        print("[ok] kpi.jsonl += %s（行数 %d → %d）" % (R, len(have), len(back)))

    # ---------- 4) verification-registry ----------
    regp = os.path.join(REPO, "docs/verification-registry.json")
    reg = jload(regp)
    gen = {
        "evidence_kind": "artifact",
        "pin_status": "frozen",
        "pin_reason": "archived-per-round",
        "artifact_sha12": sha256_file(os.path.join(RD, "report-r621.md"))[:12],
        "instrument": RDP + "/judge_r621.py",
        "instrument_sha12": sha256_file(os.path.join(RD, "judge_r621.py"))[:12],
        "binding": "audit-pin",
        "audited_by_round": R,
    }
    if any(r.get("id") == RID for r in reg["rows"]):
        for r in reg["rows"]:
            if r.get("id") == RID:
                if r.get("evidence_generated_with") != gen:
                    r["evidence_generated_with"] = gen
                    kw, txt = jdump_same_shape(regp, reg)
                    write_text(regp, txt)
                    print("[ok] registry 重钉 %s gen=%s" % (RID, gen["artifact_sha12"]))
                else:
                    print("[skip] registry %s gen 已一致（幂等）" % RID)
        return 0

    cap = ("RF0004.2 · M3 **第五刀 = 等价面分辨率取证 + 判据分级**。R620 已把「映射面为空 ∧ plan 非空 ⇒ "
           "回退读 plan」的触发前提造出来并测到回退真机行使 9/9，但其等价面判据 J6（回退面 == 轴关面）在"
           "逐跑次用例数摆动（48..58）下**无分辨率**，且判据器把该机制面次级 FAIL 编码进 `instrument_defects`"
           "（`rc = 2 if defects else 0`）⇒ 整轮被标「禁作被测结论」。本轮**零产品源码改动**（复用 R619 AOT 件"
           "逐字节，sha a184d731…），只做两件器具面补救：① **rc 分级 v4**（J6 移出 instrument_defects ⇒ "
           "0 = 主判据无红 / 1 = 机制面次级红 / 2 = 器具缺陷 / 3 = 输入缺失）；② **reps 3→6/窗** 并把 J6 "
           "三态化（EQUIVALENT / NON_REGRESSION_DETECTED / NO_RESOLUTION，阈值 = **同臂逐跑次用例数极差**，"
           "数据派生非人为常数）。真机 %d 跑次（T×%d / C×%d / C1×%d，窗集 %s）。"
           "**读数**：J0=%s（两臂前缀同源 ∧ == legacy 锚 ⇒ held-constant 真生效）· J1=%s（回退行使 %s/%s，"
           "三态 %s）· J6=%s（state=%s，Δ中位(C−T)=%s）· rc=%s / mechanism_rc=%s；铁律 11 precond rc=%s。"
           "**未成立/未判明**：见 `verdict-r621.json` 的 `honest_bounds` 与 `checks_posthoc`（NO_RESOLUTION "
           "不得读作零回归、不得读作通过；质量轴 n=6/窗 仍欠功率，只作并列）。") % (
        sum(RUNS.values()), RUNS["T"], RUNS["C"], RUNS["C1"], "..".join([WINDOWS[0], WINDOWS[-1]]),
        j0.get("pass"), j1.get("pass"), b1.get("runs_plan_fallback"), b1.get("runs_face_covered"),
        j1.get("J1e_fallback_three_state"), j6.get("pass"), j6st,
        j6.get("delta_median_C_minus_T"), vd.get("rc"), vd.get("mechanism_rc"), pre.get("rc", "N/A"))
    row = {
        "id": RID,
        "round": R,
        "owner_round": R,
        "level": "L4",
        "evidence_generated_with": gen,
        "capability": cap,
        "evidence_path": RDP + "/report-r621.md",
        "evidence_cmd": "python3 %s/closeout_r621.py --check && python3 eval/capability/status_gen.py --check" % RDP,
        "negative_control": ("① **影子自检**（`selftest_judge_r621.py`，零被测执行、纯合成日志）：11 条逐条断言，"
                             "含「Δ 符号写反」翻转负控（R620 的 J6 状态机首版即被它抓到比较变量写反 ⇒ 改代码不放宽断言），"
                             "未过 ⇒ 器具不可用（rc=2）；② **前提闸**（起臂前 1 跑次）：legacy 档必须证「候选键未到达 ∧ "
                             "exec_source=plan_fallback ∧ 前缀 == legacy 锚」，否则零臂起跑（rc=5，premise-r621.json）；"
                             "③ **J6 内含对照组**（轴关面 C 逐窗 rc 多重集/用例数）⇒ 摆动可辨；④ 判据分级负控："
                             "J6 三态为 NO_RESOLUTION 时 rc **不得**变红（不可判 ≠ 未通过），有状态机单测覆盖。"),
        "covers": ["F_env.gate.ceiling_mb", "F_merge.gate.precondition_rc", "F_orch.cost.calls_sum",
                   "F_merge.cost.new_prompt_sum", "F_merge.cache.hit_v_all", "F_merge.quality.allpass"],
        "runs": sum(RUNS.values()),
        "verdict": ("机制面见 mechanism_rc=%s · rc=%s（v4 分层：低 1 档于 R620 的 rc=2 码位不同，二者**不可直接并列**）"
                    "· J6=%s · precond rc=%s" % (vd.get("mechanism_rc"), vd.get("rc"), j6st, pre.get("rc", "N/A"))),
        "aot": "未重发布（本轮零产品源码改动 ⇒ 复用 R619 AOT 件逐字节，bins-r621.json 钉 sha）",
    }
    reg["rows"].append(row)
    reg["updated_round"] = R
    kw, txt = jdump_same_shape(regp, reg)
    write_text(regp, txt)
    back = jload(regp)
    assert back["rows"][-1]["id"] == RID and back["updated_round"] == R, "[FAIL] registry 写回读不一致"
    print("[ok] registry += %s（shape %s）" % (RID, kw))
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check_mode())
    sys.exit(main())
