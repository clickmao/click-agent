#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R567 预注册 (先写后跑) + 冻结件登记: 零远端 / 零产品改动 / 零新增夹具与开关。

与 R566 的唯一来源差异 (逐条): 窗集 w125..w130 → w131..w136; 臂集 B0(轴0)+B1(轴1) → B0(轴0)+B3(轴3);
候选④行使臂 agentB0 → agentB3; 起手闸 prev-postcheck 由 R565 件改指 R566 件 (swing 70 ⇒ REQ 2720)。
"""
import hashlib, io, json, os, shutil, sys

REPO = "/home/agentuser/AgentFramework"
PDIR = os.path.join(REPO, "eval/rover/r567")
SRC = os.path.join(REPO, "eval/rover/r560")
WINS = ["w131", "w132", "w133", "w134", "w135", "w136"]
ARMS = ["C1", "R567B0", "R567B3"]
TASKSET_SHA = "e0c667c2a313c04b2d87ac06fcba9f50166a4a0be5d5162cabdbf520d9d3927a"
BIN_SHA = "320d0eb17e709d15ce7d149ceff45fc1cacff814ac01b9fbda67f702726cee48"
PROMPT_SHA = "516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3"


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def main():
    # --- 1 冻结件逐字节复制 + 登记 (前置器按 --round 自动发现, 缺件即 DISCOVER_FAIL) ---
    ts_src = os.path.join(SRC, "taskset-r560.json")
    ts_dst = os.path.join(PDIR, "taskset-r567.json")
    if sha(ts_src) != TASKSET_SHA:
        print("[致命] 冻结题集 sha 不符: %s" % sha(ts_src)); return 3
    shutil.copyfile(ts_src, ts_dst)
    cases_dst = os.path.join(PDIR, "cases")
    if os.path.isdir(cases_dst):
        shutil.rmtree(cases_dst)
    shutil.copytree(os.path.join(SRC, "cases"), cases_dst)
    reg = {"round": "R567", "note": "冻结件逐字节复用登记 (复用不复制语义 ⇒ 原件零改动; 副本在此登记供 --round 自动发现)",
           "source_round": "R560", "taskset": {"src": "eval/rover/r560/taskset-r560.json",
                                               "dst": "eval/rover/r567/taskset-r567.json",
                                               "src_sha256": sha(ts_src), "dst_sha256": sha(ts_dst)},
           "cases": []}
    for root, _, files in os.walk(cases_dst):
        for fn in sorted(files):
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, cases_dst)
            s = os.path.join(SRC, "cases", rel)
            reg["cases"].append({"rel": rel, "src_sha256": sha(s), "dst_sha256": sha(p),
                                 "byte_identical": sha(s) == sha(p)})
    reg["all_byte_identical"] = (reg["taskset"]["src_sha256"] == reg["taskset"]["dst_sha256"]
                                and all(c["byte_identical"] for c in reg["cases"]))
    json.dump(reg, io.open(os.path.join(PDIR, "frozen-reuse-registration-r567.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[冻结件] taskset sha=%s cases=%d all_byte_identical=%s" % (
        reg["taskset"]["dst_sha256"][:16], len(reg["cases"]), reg["all_byte_identical"]))
    if not reg["all_byte_identical"]:
        return 3

    # --- 2 预注册 (runner 第 0 步机检 5 项) ---
    pre = {
        "round": "R567",
        "written_before_run": True,
        "author": "cron-agent (60min tick, 2026-09-19)",
        "claim": "**同窗零开发对照轮 (第二窗集)**: 既有开关 `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 的值 "
                 "**0 vs 3** (同一枚二进制, 同题面/夹具/role/判分器逐字节复用) × 外部真值 codex ⇒ 回答"
                 "「R566 单变量 0-vs-1 无增益 (两档均不过判据 v2) 是否剂量档位选择所致」, 并使候选④ "
                 "C4-1/2/3 **全部被真实行使** (行使臂 B0→B3: R566 实测 B0 每窗恒 1 次调用 ⇒ C4-3 不可判)。"
                 "零产品源码改动 / 零新增夹具 / 零新增开关 (用户令 2026-09-18「开工, 不许新增夹具和额外开发了」)。",
        "one_time_context": "用户令 2026-09-19「继续下一轮」⇒ 按 R566 收口时登记的零开发路径执行; "
                            "不重开器具/文档/预注册线, 不推进 exp1 backlog 器具类候选。",
        "candidates_ledger": {
            "R567-① 同窗单变量 0 vs 3 (本窗集)": "做 —— 承重候选; 与 w119..w124 / w125..w130 **并列不相减**",
            "R567-② 候选④ C4 行使臂换 B3": "做 —— 判据 C4-1/2/3 文本不变, 只换行使臂; 若本轮仍无第 2 次调用 ⇒ 如实登记「未行使」",
            "R567-③ 起手闸振幅余量条款 (prev=R566 swing 70)": "做 —— REQ = 2650 + 70 = 2720 (只翻既有闸 --gate-mb)",
            "R567-④ exp1 backlog 器具类剩余候选": "未做 —— 与用户 2026-09-17 方向逆转 (器具/登记/文档回填判封存) 冲突 ⇒ 只登记",
            "R567-⑤ 两项待放行 (契约加厚/落点自验、rc=5/8 交付闸)": "未做 —— 须动契约/产品分支 ⇒ 未放行, 只在报告写「待放行」",
        },
        "single_variable": "**仅一个 env 开关的值**: `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` ∈ {0 (R567B0), 3 (R567B3)};"
                           " 全臂共用同一枚 AOT 二进制 (sha %s, runner 第 0 步机检), 题面/夹具/role/窗口逐字节同" % BIN_SHA[:16],
        "arms": {
            "C1": {"side": "codex", "desc": "外部真值 (另一套 agent 框架 CLI, 同模型 deepseek-flash, 同题面同夹具同窗)", "env": {}},
            "R567B0": {"side": "agent", "desc": "执行回灌修复轴 = 0 (关)", "env": {"AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR": "0"}},
            "R567B3": {"side": "agent", "desc": "执行回灌修复轴 = 3 (剂量档; R560 剂量轴另一档)", "env": {"AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR": "3"}},
        },
        "arm_env_definition_note": "两臂剂量键**都显式落盘**且只有这一个键取值不同 ⇒ 单变量由构造保证; runner 第 0 步机检 "
                                   "「两臂剂量键集 == {AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR} 且取值 0 / 3」。其余 env 全臂相同: "
                                   "AGENTFRAMEWORK_R1_CONTRACT=1 ∧ R1_MAX_REPAIR=1 (runner export) ∧ PUBLIC_SELFCHECK=1 ∧ ROLE_FILE ∧ TRANSCRIPT ∧ WORKSPACE ∧ TAG。",
        "scope_declaration": {
            "windows": WINS, "window_count": 6,
            "task": "g1 (冻结题面; prompt sha256 与 R559/R560/R563/R565/R566 逐字节相同)",
            "task_prompt_sha256_expected": PROMPT_SHA,
            "binary_sha256_expected": BIN_SHA,
            "hidden_cases": 58,
            "cross_round_deltas_forbidden": "与 w104..w118 / w119..w124 / w125..w130 的读数**并列不相减** (新窗, 非同一窗集延续)",
        },
        "criterion_version": "v2 (逐窗并列 + 真值崩窗 unreliable[MARGIN=3] + 配对判据[无窗<=-3 且 配对中位>=-2, n>=3] + VOID 臂窗单列) "
                             "—— 口径文本取自 docs/external-reference-harness.md §12 (R562 入册), 本文件只引用不重定义; **本轮不改判据**",
        "acceptance_rule": {
            "primary": "判据 v2 判决 (eval/rover/r561/verdict_r561.py 装置, adjudicate_r567.py 零逻辑复制复用)",
            "rc": "0 全过 / 1 判据未过 (被测或前提) / 2 器具缺陷 / 3 缺侧或不可判",
            "expected_direction": "**无增益预期** (零产品改动): ①若 B0 (轴关) 与 B3 (轴=3) 的配对差与 R566 (0 vs 1) **同向或更小** "
                                  "⇒ 剂量档位不是承重变量 (与 R560 剂量轴并列复核); ②若 B3 明显优于 B0 ⇒ 单列「剂量档位有效」的候选而非增益宣称。"
                                  "预注册不得由本轮读数反推期望方向。",
            "cross_check": "铁律 11 前置器 python3 eval/rover/r507pre/exec_precondition.py --round r567 (两侧产出物独立物化 + 真跑 + 逐用例判对); "
                           "rc!=0 ⇒ 全部成本/降幅读数标「参考(未可验收)」",
        },
        "gate_clause": {
            "candidate": "R564 候选③ (起手闸振幅余量条款: MARGIN = max(60MB, 上一轮**实测振幅**))",
            "derivation": "prev_postcheck = eval/rover/r566/gate-postcheck-r566.json (swing_mb=70) ⇒ MARGIN = 70; REQ = 2650 + 70 = 2720 "
                          "(只翻既有闸 --gate-mb, 零新逻辑进闸)",
            "consecutive": 2,
            "controls": {"PC": "连续 2 次 preflight_gate --gate-mb REQ ⇒ 期望 PASS ×2",
                         "NC_hog": "400MB 占用 ⇒ 期望 GATE_BLOCKED",
                         "discriminating_pair": "把内存态压进判别带 [2650, REQ) 后: --gate-mb 2650 ⇒ PASS ∧ --gate-mb REQ ⇒ GATE_BLOCKED; "
                                                "带内不可达 ⇒ rc=3 如实登记「真判别未行使」(不当 FAIL)"},
            "fail_closed": "REQ 派生失败或顶棚 < REQ ⇒ rc=2 不起臂 (不静默放行)",
        },
        "candidate4": {
            "name": "判定输入指纹 / 命中率双口径复核 (新窗; 承 R565/R566 候选④)",
            "exercise_arm": "R567B3 (本轴 3 档) —— R566 行使臂 R566B0 每窗恒 1 次调用 ⇒ C4-3 敏感性不可判; "
                            "换臂理由 = 使 C4-1/2/3 **全部被真实行使**; 判据 C4-1/2/3 文本**不变**",
            "pre_registered_checks": {
                "C4-1 恒等式": "每个中继 dump: prompt_tokens == hit + miss ∧ 0 <= hit <= prompt (违反 >0 ⇒ rc=2 器具/口径缺陷)",
                "C4-2 确定性": "行使臂每窗**第 1 次调用**的 prompt sha8 全窗相同 ∧ transcript 任务/前缀 sha 全窗相同",
                "C4-3 非平凡": "call1 vs call2 的 prompt sha 跨窗**互异** (确定性 ≠ 恒定输出)",
                "C4-4 命中率双口径": "v_all(含冷启动) / v_incr(去冷启动) 逐窗出数; 未上报记哨兵不入比率",
            },
            "rc": "0 全过 / 2 违反 / 3 输入缺失; 未行使 ⇒ 记 honest_boundary, 不改判据",
        },
        "artifacts": [
            "eval/rover/r567/prereg-r567.json (本件, 先写后跑)",
            "eval/rover/r567/frozen-reuse-registration-r567.json (冻结件逐字节复用登记)",
            "eval/rover/r567/gate-margin-r567.json (条款派生 + 成对控制 + 运行中振幅)",
            "eval/rover/r567/fingerprint-r567.json (候选④, 行使臂 = agentB3)",
            "eval/rover/r567/kpi-table-r567.json (调用/新算 prompt/completion/命中率双口径, 三臂)",
            "eval/rover/r567/percase-matrix-r567.json (逐例矩阵, 判分对副本)",
            "eval/rover/r567/verdict-r567.json (判据 v2 判决)",
            "eval/rover/r567/precond-r567.json (铁律 11 前置器)",
            "eval/rover/r567/snapshots/<win>/{C1,R567B0,R567B3}/g1/** (冻结快照)",
        ],
        "preregistered_expectations": {
            "quality": "无增益预期 (零产品改动 ⇒ 只作读数, 不作增益宣称); 三臂同窗配对",
            "cost": "调用数/新算 prompt/completion 三列分列 (禁名义总量); B3 的 completion 预期不低于 B0 (剂量更高 ⇒ 修复调用更多)",
            "honest_boundary": "g1 族的 wythoff 失分在 R562/R564 已两次定因 (产物缺陷); 本轮**不修** (未放行) ⇒ 铁律 11 rc=1 的可能性高, 不得据此改写判据",
        },
        "notes": "本文件先写后跑 (runner 第 0 步机检: round / 臂集 3 / require 18 / criterion_version v2 / 两臂剂量键集与取值 0 vs 3)。"
                 "判据 v2 口径不在本文件重定义, 只引用 docs/external-reference-harness.md §12。",
        "evidence_scope": {"require": ["%s/%s" % (w, a) for w in WINS for a in ARMS]},
    }
    json.dump(pre, io.open(os.path.join(PDIR, "prereg-r567.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[预注册] arms=%s require=%d" % (sorted(pre["arms"]), len(pre["evidence_scope"]["require"])))

    d = json.load(io.open(os.path.join(PDIR, "prereg-r567.json"), encoding="utf-8"))
    assert d["round"] == "R567" and d["written_before_run"] is True
    assert set(d["arms"]) == {"C1", "R567B0", "R567B3"}
    assert len(d["evidence_scope"]["require"]) == 18
    assert str(d["criterion_version"]).startswith("v2")
    assert d["candidate4"]["exercise_arm"].startswith("R567B3")
    doses = {a: int(d["arms"][a]["env"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"]) for a in ("R567B0", "R567B3")}
    assert doses == {"R567B0": 0, "R567B3": 3}, doses
    # 窗口名与上一轮互斥 (防端口遗漏: 新窗集不得与 R566 窗集重叠)
    assert not (set(WINS) & {"w125", "w126", "w127", "w128", "w129", "w130"}), WINS
    print("[机检] 预注册 6 项全过 (dose=%s, wins=%s)" % (doses, WINS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
