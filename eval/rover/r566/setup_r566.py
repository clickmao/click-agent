#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R566 预注册 (先写后跑) + 冻结件登记: 零远端 / 零产品改动 / 零新增夹具与开关。"""
import hashlib, io, json, os, shutil, sys

REPO = "/home/agentuser/AgentFramework"
PDIR = os.path.join(REPO, "eval/rover/r566")
SRC = os.path.join(REPO, "eval/rover/r560")
WINS = ["w125", "w126", "w127", "w128", "w129", "w130"]
ARMS = ["C1", "R566B0", "R566B1"]
TASKSET_SHA = "e0c667c2a313c04b2d87ac06fcba9f50166a4a0be5d5162cabdbf520d9d3927a"
BIN_SHA = "320d0eb17e709d15ce7d149ceff45fc1cacff814ac01b9fbda67f702726cee48"
PROMPT_SHA = "516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3"


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def main():
    # --- 1 冻结件逐字节复制 + 登记 (承 R565: 前置器按 --round 自动发现, 缺件即 DISCOVER_FAIL) ---
    ts_src = os.path.join(SRC, "taskset-r560.json")
    ts_dst = os.path.join(PDIR, "taskset-r566.json")
    if sha(ts_src) != TASKSET_SHA:
        print("[致命] 冻结题集 sha 不符: %s" % sha(ts_src)); return 3
    shutil.copyfile(ts_src, ts_dst)
    cases_dst = os.path.join(PDIR, "cases")
    if os.path.isdir(cases_dst):
        shutil.rmtree(cases_dst)
    shutil.copytree(os.path.join(SRC, "cases"), cases_dst)
    reg = {"round": "R566", "note": "冻结件逐字节复用登记 (复用不复制语义 ⇒ 原件零改动; 副本在此登记供 --round 自动发现)",
           "source_round": "R560", "taskset": {"src": "eval/rover/r560/taskset-r560.json",
                                               "dst": "eval/rover/r566/taskset-r566.json",
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
    json.dump(reg, io.open(os.path.join(PDIR, "frozen-reuse-registration-r566.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[冻结件] taskset sha=%s cases=%d all_byte_identical=%s" % (
        reg["taskset"]["dst_sha256"][:16], len(reg["cases"]), reg["all_byte_identical"]))
    if not reg["all_byte_identical"]:
        return 3

    # --- 2 预注册 (runner 第 0 步机检 5 项) ---
    pre = {
        "round": "R566",
        "written_before_run": True,
        "author": "cron-agent (60min tick, 2026-09-19T03:0x)",
        "claim": "**同窗单变量对照轮**: 既有开关 `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 的值 "
                 "**0 vs 1** (同一枚二进制, 同题面同夹具同窗) × 外部真值 codex ⇒ 判定"
                 "「R565 真默认档的失分是**预算不足**还是**生成/修复面不足**」, 并给出 "
                 "**completion 压缩** (RF0001.3 出口闸: 新算 prompt/completion 双列不劣化 ∧ 质量不降) 的同窗读数。"
                 "零产品源码改动 / 零新增夹具 / 零新增开关 (用户令 2026-09-18「开工, 不许新增夹具和额外开发了」)。",
        "candidates_ledger": {
            "R565-① matrix --work 守卫": "未做 —— 该缺陷根因 = 误用既有默认值 (--work 指向轮根); 本轮器具默认值 "
                                        "为 /tmp/r566/pc (非轮根) 且调用时不覆盖 ⇒ 零开发规避; 加守卫属新增开发, 未放行",
            "R565-② 预算轴单变量臂": "做 (本轮的臂集 B0 vs B1) —— 承重候选",
            "R565-③ exp1 backlog 剩余候选": "未做 —— 与用户 2026-09-17 方向逆转 (器具/登记/文档回填判封存) 冲突 ⇒ 只登记",
            "R564-①/② wythoff 族修复 / 交付闸": "未做 —— 须动契约/产品分支 ⇒ 用户 2026-09-18 令未放行",
        },
        "single_variable": "**仅一个 env 开关的值**: `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` ∈ {0 (R566B0), 1 (R566B1)};"
                           " 全臂共用同一枚 AOT 二进制 (sha %s, runner 第 0 步机检), 题面/夹具/role/窗口逐字节同" % BIN_SHA[:16],
        "arms": {
            "C1": {"side": "codex", "desc": "外部真值 (另一套 agent 框架 CLI, 同模型 deepseek-flash, 同题面同夹具同窗)", "env": {}},
            "R566B0": {"side": "agent", "desc": "执行回灌修复轴 = 0 (关)", "env": {"AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR": "0"}},
            "R566B1": {"side": "agent", "desc": "执行回灌修复轴 = 1 (产品默认值)", "env": {"AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR": "1"}},
        },
        "arm_env_definition_note": "两臂剂量键**都显式落盘**且只有这一个键取值不同 ⇒ 单变量由构造保证; runner 第 0 步机检 "
                                   "「两臂剂量键集 == {AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR} 且取值 0 / 1」。其余 env 全臂相同: "
                                   "AGENTFRAMEWORK_R1_CONTRACT=1 ∧ R1_MAX_REPAIR=1 (runner export) ∧ PUBLIC_SELFCHECK=1 ∧ ROLE_FILE ∧ TRANSCRIPT ∧ WORKSPACE ∧ TAG。",
        "scope_declaration": {
            "windows": WINS, "window_count": 6,
            "task": "g1 (冻结题面; prompt sha256 与 R559/R560/R563/R565 逐字节相同)",
            "task_prompt_sha256_expected": PROMPT_SHA,
            "binary_sha256_expected": BIN_SHA,
            "hidden_cases": 58,
            "cross_round_deltas_forbidden": "与 w104..w118 / w119..w124 的读数**并列不相减** (新窗, 非同一窗集延续)",
        },
        "criterion_version": "v2 (逐窗并列 + 真值崩窗 unreliable[MARGIN=3] + 配对判据[无窗<=-3 且 配对中位>=-2, n>=3] + VOID 臂窗单列) "
                             "—— 口径文本取自 docs/external-reference-harness.md §12 (R562 入册), 本文件只引用不重定义",
        "acceptance_rule": {
            "primary": "判据 v2 判决 (eval/rover/r561/verdict_r561.py 装置, adjudicate_r566.py 零逻辑复制复用)",
            "rc": "0 全过 / 1 判据未过 (被测或前提) / 2 器具缺陷 / 3 缺侧或不可判",
            "expected_direction": "**无增益预期** (零产品改动): 本轮只做**判据前提面**的判定 —— ①若 B0 (轴关) 在配对上不低于 B1 (轴开) "
                                  "⇒ 失分不是预算不足 (承重结论) 且 completion/新算 prompt 双列**显著更低** ⇒ RF0001.3 压缩候选成立; "
                                  "②若 B0 明显低于 B1 ⇒ 预算仍是承重变量, 与 R560 (dose 3 中位 52.5 < dose 0 中位 54.0) 并列不相减地单列。"
                                  "预注册不得由本轮读数反推期望方向。",
            "cross_check": "铁律 11 前置器 python3 eval/rover/r507pre/exec_precondition.py --round r566 (两侧产出物独立物化 + 真跑 + 逐用例判对); "
                           "rc!=0 ⇒ 全部成本/降幅读数标「参考(未可验收)」",
        },
        "gate_clause": {
            "candidate": "R564 候选③ (起手闸振幅余量条款: MARGIN = max(60MB, 上一轮**实测振幅**))",
            "derivation": "prev_postcheck = eval/rover/r565/gate-postcheck-r565.json ⇒ MARGIN = 其实测 swing_mb; REQ = 2650 + MARGIN (只翻既有闸 --gate-mb, 零新逻辑进闸)",
            "consecutive": 2,
            "controls": {"PC": "连续 2 次 preflight_gate --gate-mb REQ ⇒ 期望 PASS ×2",
                         "NC_hog": "400MB 占用 ⇒ 期望 GATE_BLOCKED",
                         "discriminating_pair": "把内存态压进判别带 [2650, REQ) 后: --gate-mb 2650 ⇒ PASS ∧ --gate-mb REQ ⇒ GATE_BLOCKED; "
                                                "带内不可达 ⇒ rc=3 如实登记「真判别未行使」(不当 FAIL)"},
            "fail_closed": "REQ 派生失败或顶棚 < REQ ⇒ rc=2 不起臂 (不静默放行)",
        },
        "candidate4": {
            "name": "判定输入指纹 / 命中率双口径复核 (新窗; 承 R565 候选④)",
            "pre_registered_checks": {
                "C4-1 恒等式": "每个中继 dump: prompt_tokens == hit + miss ∧ 0 <= hit <= prompt (违反 >0 ⇒ rc=2 器具/口径缺陷)",
                "C4-2 确定性": "R566B0 每窗**第 1 次调用**的 prompt sha8 全窗相同 ∧ transcript 任务/前缀 sha 全窗相同",
                "C4-3 非平凡": "call1 vs call2 的 prompt sha 跨窗**互异** (确定性 ≠ 恒定输出)",
                "C4-4 命中率双口径": "v_all(含冷启动) / v_incr(去冷启动) 逐窗出数; 未上报记哨兵不入比率",
            },
            "rc": "0 全过 / 2 违反 / 3 输入缺失",
        },
        "artifacts": [
            "eval/rover/r566/prereg-r566.json (本件, 先写后跑)",
            "eval/rover/r566/frozen-reuse-registration-r566.json (冻结件逐字节复用登记)",
            "eval/rover/r566/gate-margin-r566.json (条款派生 + 成对控制 + 运行中振幅)",
            "eval/rover/r566/fingerprint-r566.json (候选④)",
            "eval/rover/r566/kpi-table-r566.json (调用/新算 prompt/completion/命中率双口径, 三臂)",
            "eval/rover/r566/percase-matrix-r566.json (逐例矩阵, 判分对副本)",
            "eval/rover/r566/verdict-r566.json (判据 v2 判决)",
            "eval/rover/r566/precond-r566.json (铁律 11 前置器)",
            "eval/rover/r566/snapshots/<win>/{C1,R566B0,R566B1}/g1/** (冻结快照)",
        ],
        "preregistered_expectations": {
            "quality": "无增益预期 (零产品改动 ⇒ 只作读数, 不作增益宣称); 三臂同窗配对",
            "cost": "调用数/新算 prompt/completion 三列分列 (禁名义总量); B0 的 completion 预期低于 B1 (少一次回灌调用)",
            "honest_boundary": "g1 族的 wythoff 失分在 R562/R564 已两次定因 (产物缺陷); 本轮**不修** (未放行) ⇒ 铁律 11 rc=1 的可能性高, 不得据此改写判据",
        },
        "notes": "本文件先写后跑 (runner 第 0 步机检: round / 臂集 3 / require 18 / criterion_version v2 / 两臂剂量键集与取值)。"
                 "判据 v2 口径不在本文件重定义, 只引用 docs/external-reference-harness.md §12。",
        "evidence_scope": {"require": ["%s/%s" % (w, a) for w in WINS for a in ARMS]},
    }
    json.dump(pre, io.open(os.path.join(PDIR, "prereg-r566.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[预注册] arms=%s require=%d" % (sorted(pre["arms"]), len(pre["evidence_scope"]["require"])))
    d = json.load(io.open(os.path.join(PDIR, "prereg-r566.json"), encoding="utf-8"))
    assert d["round"] == "R566" and d["written_before_run"] is True
    assert set(d["arms"]) == {"C1", "R566B0", "R566B1"}
    assert len(d["evidence_scope"]["require"]) == 18
    assert str(d["criterion_version"]).startswith("v2")
    doses = {a: int(d["arms"][a]["env"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"]) for a in ("R566B0", "R566B1")}
    assert doses == {"R566B0": 0, "R566B1": 1}, doses
    print("[机检] 预注册 5 项全过 (dose=%s)" % doses)
    return 0


if __name__ == "__main__":
    sys.exit(main())
