#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R569 派生 + 预注册 (先写后跑) 器具。

本轮 = **零开发**对照轮 (用户令 2026-09-18「开工, 不许新增夹具和额外开发了」)：
既有开关 `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 取值 **0 vs 3** × 外部真值 codex，6 **新**窗 w137..w142。

与来源轮 R567 的差异 (逐条声明, 其余逐字节继承):
  ① 命名空间 R567→R569 / r567→r569 / 窗集 w131..w136 → w137..w142 / 工作目录 /tmp/r569 / 端口 49447→49511;
  ② **候选③ 追加两条预注册规则** (承 R568 补记面): 「逐窗回退窗点名」+「交付前自测闸**拒收窗**排除规则」
     —— 后者即 R568 所称「臂级崩溃窗」的**更名与定因** (R569 候选④ 实测: 该窗是产品 fail-closed 自测闸
     rc=8 `public_probe_unmet` 行使窗, **不是运行级崩溃**);
  ③ **候选⑤ 器具修订**: 起手闸余量条款加**上界** `MARGIN := min(max(FLOOR, prev_swing), ceiling - GATE)`
     (R568 预注册的下一轮规则), 顶棚装不下下限时 fail-closed (rc=2), 装得下但 < 观测振幅时置
     `margin_capped=true` (不得静默) ⇒ 器具改版 ⇒ 保形重钉 + 成对控制重跑 (skill 纪律);
  ④ 起手闸 prev-postcheck 由 R566 件改指 **R567** 件 (swing_mb=103)。

零产品源码改动 / 零新增夹具 / 零新增开关; 冻结题集与用例脚本逐字节复用 (复用不复制语义)。
"""
import hashlib
import io
import json
import os
import re
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
PDIR = os.path.join(REPO, "eval/rover/r569")
SRC = os.path.join(REPO, "eval/rover/r567")
FREEZE_SRC = os.path.join(REPO, "eval/rover/r560")
WINS = ["w137", "w138", "w139", "w140", "w141", "w142"]
WINS_PREV = ["w131", "w132", "w133", "w134", "w135", "w136"]
ARMS = ["C1", "R569B0", "R569B3"]
TASKSET_SHA = "e0c667c2a313c04b2d87ac06fcba9f50166a4a0be5d5162cabdbf520d9d3927a"
BIN_SHA = "320d0eb17e709d15ce7d149ceff45fc1cacff814ac01b9fbda67f702726cee48"
PROMPT_SHA = "516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3"
GRAder_SHA_EXP = "a67215a7"

# 需派生的器具文件 (源 → 目标)。逐字节继承 + 声明式替换。
DERIVED = ["run_r567.sh", "ingest_r567.py", "fingerprint_r567.py", "kpi_r567.py",
           "matrix_r567.py", "adjudicate_r567.py", "gate_margin_r567.py",
           "mem_sampler.py", "mem_sample_once.py"]


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def win_map():
    m = {}
    for a, b in zip(WINS_PREV, WINS):
        m[a] = b
    return m


def substitute(text, path):
    """声明式替换: 轮号/目录/窗号/端口; 返回 (新文本, 替换计数)。"""
    n = {}
    rules = []
    # 窗号 (先做, 避免被后续规则破坏)
    for a, b in win_map().items():
        rules.append((a, b))
    rules += [("w125..w130", "w131..w136"),
              ("R567", "R569"), ("r567", "r569"),
              ("WIN0=${WIN0:-131}", "WIN0=${WIN0:-137}"),
              ("49447", "49511")]
    out = text
    for a, b in rules:
        c = out.count(a)
        if c:
            out = out.replace(a, b)
            n[a] = c
    return out, n


def derive_files():
    """派生器具文件 + 落盘差异清单 (机检: 只声明式差异, 无意外改动)。"""
    os.makedirs(PDIR, exist_ok=True)
    man = {"round": "R569", "source_round": "R567", "note":
           "派生件清单 (器具改 ⇒ 须重审 + 保形重钉): 每条给出源/目标 sha256 与替换计数",
           "files": []}
    for fn in DERIVED:
        src = os.path.join(SRC, fn)
        dst_name = fn.replace("r567", "r569").replace("R567", "R569")
        dst = os.path.join(PDIR, dst_name)
        txt = io.open(src, encoding="utf-8").read()
        new, counts = substitute(txt, src)
        io.open(dst, "w", encoding="utf-8").write(new)
        man["files"].append({"src": "eval/rover/r567/%s" % fn, "dst": "eval/rover/r569/%s" % dst_name,
                             "src_sha256": sha(src), "dst_sha256": sha(dst),
                             "substitutions": counts,
                             "n_lines_src": txt.count("\n"), "n_lines_dst": new.count("\n")})
    # 源目录零改动断言 (派生不写源)
    man["source_unchanged"] = all(
        sha(os.path.join(SRC, fn)) == f["src_sha256"] for fn, f in zip(DERIVED, man["files"]))
    json.dump(man, io.open(os.path.join(PDIR, "derivation-manifest-r569.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    ok = all(f["n_lines_src"] == f["n_lines_dst"] for f in man["files"])
    print("[派生] files=%d source_unchanged=%s line_counts_equal=%s"
          % (len(man["files"]), man["source_unchanged"], ok))
    return man


def gate_patch():
    """候选⑤: 起手闸条款加上界 (ceiling - GATE) + margin_capped 可见 + 成对控制换臂。

    只改 gate_margin_r569.py 内的 derive()/selftest() 两处; 其余逐字节继承派生件。
    断言不放宽: 顶棚装不下**下限** ⇒ rc=2 (fail-closed); 装得下但 < 目标余量 ⇒ 行使 + 显式 capped。
    """
    p = os.path.join(PDIR, "gate_margin_r569.py")
    txt = io.open(p, encoding="utf-8").read()
    old_derive = """    ceil_mb, spread = max(xs), max(xs) - min(xs)
    margin = max(MARGIN_FLOOR, float(prev_swing_mb or 0))
    required = GATE_MB + margin
    margin_low = ceil_mb < required
    ok = (ceil_mb >= required) and (spread <= SPREAD_MAX)
    return {"rc": 0 if ok else 2,"""
    new_derive = """    ceil_mb, spread = max(xs), max(xs) - min(xs)
    want = max(MARGIN_FLOOR, float(prev_swing_mb or 0))   # 目标余量 (数据派生)
    cap = ceil_mb - GATE_MB                                # 上界: 顶棚允许的最大余量
    # 候选⑤ (R568 预注册的下一轮规则): MARGIN := min(目标, 顶棚 - GATE)
    # 上界**不得静默**: 装不下下限 ⇒ fail-closed (rc=2); 装得下但 < 目标 ⇒ 行使 + margin_capped=True
    margin = min(want, cap)
    capped = margin < want
    floor_unreachable = cap < MARGIN_FLOOR
    required = GATE_MB + margin
    margin_low = ceil_mb < required
    ok = (not floor_unreachable) and (ceil_mb >= required) and (spread <= SPREAD_MAX)
    return {"rc": 0 if ok else 2,
            "margin_want_mb": round(want, 1), "margin_cap_mb": round(cap, 1),
            "margin_capped": bool(capped), "floor_unreachable": bool(floor_unreachable),"""
    assert old_derive in txt, "derive() 锚点未命中 ⇒ 派生件与预期不符 (fail-closed)"
    txt = txt.replace(old_derive, new_derive)

    old_why = """            "why": ("ok" if ok else
                    ("spread_too_wide" if spread > SPREAD_MAX else "ceiling_below_required_margin")),"""
    new_why = """            "why": ("ok" if ok else
                    ("margin_floor_unreachable_at_ceiling" if floor_unreachable else
                     ("spread_too_wide" if spread > SPREAD_MAX else "ceiling_below_required_margin"))),"""
    assert old_why in txt, "why 锚点未命中"
    txt = txt.replace(old_why, new_why)

    old_clause = '''            "clause": "起手读数 >= GATE_MB(%d) + MARGIN(max(%d, 上一轮观测振幅)) 且 极差 <= %d 且 连续 2 次 且 blockers 空"
                      % (GATE_MB, MARGIN_FLOOR, SPREAD_MAX)}'''
    new_clause = '''            "clause": "起手读数 >= GATE_MB(%d) + MARGIN(min(max(%d, 上一轮观测振幅), 顶棚-GATE_MB)) "
                      "且 极差 <= %d 且 连续 2 次 且 blockers 空; 上界生效时 margin_capped=true (不静默), "
                      "顶棚装不下下限时 fail-closed rc=2"
                      % (GATE_MB, MARGIN_FLOOR, SPREAD_MAX)}'''
    assert old_clause in txt, "clause 锚点未命中"
    txt = txt.replace(old_clause, new_clause)

    old_st = txt[txt.index("def selftest():"):txt.index("def main():")]
    new_st = '''def selftest():
    """成对控制 (器具改版后重钉): 正控 3 + 负控 3, 逐例断言 rc **与** margin_capped。

    与 R567 版的语义变化 (声明): 旧负控 `NC_v1_constant_unreachable` (期望 rc=2) 在上界规则下
    **不再成立** —— 常量 200 被上界夹到 163 后条款可行使 ⇒ 该例改为正控 `PL_v1_constant_capped`
    (期望 rc=0 **且** margin_capped=True: 证明「不该静的」没被静默)。真正的负控改成
    「顶棚连下限都装不下」(cap < MARGIN_FLOOR) ⇒ rc=2。
    """
    cases = [
        ("PL_floor_healthy", [2851, 2854, 2856], None, 0, False),        # 正控: 下限档
        ("PL_adaptive_prev110", [2813, 2811, 2812], 110, 0, False),      # 正控: 自适应档
        ("PL_capped_at_ceiling", [2704, 2703, 2704], 103, 0, True),      # 正控: R568 实测复现 (上界行使)
        ("PL_v1_constant_capped", [2813, 2811, 2812], 200, 0, True),     # 正控: 旧 v1 常量被夹 (非静默)
        ("NC_cap_below_floor", [2695, 2695, 2695], 103, 2, False),       # 负控: 顶棚装不下下限
        ("NC_marginal_2652", [2652, 2652, 2652], None, 2, False),        # 负控: R562 擦边反例
        ("NC_jitter", [2700, 2760, 2850], None, 2, False),               # 负控: 极差 150 > 50
    ]
    out = []
    for name, xs, prev, exp_rc, exp_capped in cases:
        got = derive(xs, prev)
        ok = (got["rc"] == exp_rc) and (bool(got.get("margin_capped")) == exp_capped)
        out.append({"fixture": name, "expected_rc": exp_rc, "got_rc": got["rc"],
                    "expected_capped": exp_capped, "got_capped": bool(got.get("margin_capped")),
                    "ok": ok})
    n_ok = sum(1 for x in out if x["ok"])
    return {"fixtures": out, "n": len(out), "n_ok": n_ok, "has_teeth": n_ok == len(out)}


'''
    txt = txt.replace(old_st, new_st)
    txt = txt.replace('rec.update({"round": "R569"', 'rec.update({"round": "R569"')
    io.open(p, "w", encoding="utf-8").write(txt)
    print("[候选⑤] gate_margin_r569.py 已加上界规则 (derive/why/clause/selftest 四处)")
    return sha(p)


def freeze_copy():
    """冻结题集 + 判分器用例脚本逐字节复制并登记 (复用不复制: 源零改动)。"""
    ts_src = os.path.join(FREEZE_SRC, "taskset-r560.json")
    ts_dst = os.path.join(PDIR, "taskset-r569.json")
    if sha(ts_src) != TASKSET_SHA:
        print("[致命] 冻结题集 sha 不符: %s" % sha(ts_src))
        return None
    shutil.copyfile(ts_src, ts_dst)
    cases_dst = os.path.join(PDIR, "cases")
    if os.path.isdir(cases_dst):
        shutil.rmtree(cases_dst)
    shutil.copytree(os.path.join(FREEZE_SRC, "cases"), cases_dst)
    reg = {"round": "R569", "note": "冻结件逐字节复用登记 (复用不复制语义 ⇒ 原件零改动)",
           "source_round": "R560",
           "taskset": {"src": "eval/rover/r560/taskset-r560.json",
                       "dst": "eval/rover/r569/taskset-r569.json",
                       "src_sha256": sha(ts_src), "dst_sha256": sha(ts_dst)},
           "cases": []}
    for root, _, files in os.walk(cases_dst):
        for fn in sorted(files):
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, cases_dst)
            s = os.path.join(FREEZE_SRC, "cases", rel)
            reg["cases"].append({"rel": rel, "src_sha256": sha(s), "dst_sha256": sha(p),
                                 "byte_identical": sha(s) == sha(p)})
    reg["all_byte_identical"] = (reg["taskset"]["src_sha256"] == reg["taskset"]["dst_sha256"]
                                and all(c["byte_identical"] for c in reg["cases"]))
    json.dump(reg, io.open(os.path.join(PDIR, "frozen-reuse-registration-r569.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[冻结件] taskset sha=%s cases=%d all_byte_identical=%s"
          % (reg["taskset"]["dst_sha256"][:16], len(reg["cases"]), reg["all_byte_identical"]))
    if not reg["all_byte_identical"]:
        return None
    # 判分器脚本 sha 登记 (与 R556/R559/R560/R563/R565/R566/R567 同源)
    sc = os.path.join(cases_dst, "run_cases_r521.py")
    h = sha(sc)
    print("[冻结件] 判分器 run_cases_r521.py sha=%s (期望前缀 %s) ok=%s"
          % (h[:16], GRAder_SHA_EXP, h.startswith(GRAder_SHA_EXP)))
    reg["grader_sha256"] = h
    json.dump(reg, io.open(os.path.join(PDIR, "frozen-reuse-registration-r569.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return h


def prereg(grader_sha):
    pre = {
        "round": "R569",
        "written_before_run": True,
        "author": "cron-agent (60min tick, 2026-09-19)",
        "claim": "**同窗零开发对照轮 (第三窗集)**: 既有开关 `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 的值 "
                 "**0 vs 3** (同一枚二进制, 同题面/夹具/role/判分器逐字节复用) × 外部真值 codex, 6 新窗 w137..w142。"
                 "承重问题 = R568 补记面给出的「剔拒收窗后 0v3 同窗配对 +4.31pp (p=0.0013)」在**新窗集**上是否复现, "
                 "并行使 R568 为其写下的两条新规则 (逐窗回退点名 / 拒收窗排除)。零产品源码改动 / 零新增夹具 / 零新增开关。",
        "one_time_context": "用户令 2026-09-19「继续下一轮」⇒ 按 R568 登记的零开发路径执行 (候选③④⑤ 并轮); "
                            "不重开 exp1 backlog 器具线; 两项须动契约/产品分支的候选 (①②) 未放行。",
        "candidates_ledger": {
            "R569-① 契约加厚 v3 / 产物落点自验": "未做 —— 须动契约或产品分支 ⇒ **待放行** (用户令 2026-09-18 禁新增夹具与额外开发)",
            "R569-② 交付闸/停止条件 (rc=5/rc=8 仍交付)": "未做 —— 须新增产品分支 ⇒ **待放行**; 本轮候选④ 只做**只读定因**",
            "R569-③ 剂量轴新窗集单变量 0 vs 3 (承重)": "做 —— 6 新窗 w137..w142, 3 臂同窗; 预注册含「逐窗回退窗点名」+「拒收窗排除规则」",
            "R569-④ 拒收窗 (R568 记『臂级崩溃窗』) 定因": "做 —— 零开发只读取既有日志/快照 (已完成, 见 readings)",
            "R569-⑤ MARGIN 上界规则落地 + 条款行使": "做 —— 器具改版 (上界 + capped 可见) ⇒ 保形重钉 + 成对控制重跑",
        },
        "single_variable": "**仅一个 env 开关的值**: `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` ∈ {0 (R569B0), 3 (R569B3)}; "
                           "全臂共用同一枚 AOT 二进制 (sha %s, runner 第 0 步机检), 题面/夹具/role/窗口逐字节同" % BIN_SHA[:16],
        "arms": {
            "C1": {"side": "codex", "desc": "外部真值 (另一套 agent 框架 CLI, 同模型, 同题面同夹具同窗)", "env": {}},
            "R569B0": {"side": "agent", "desc": "执行回灌修复轴 = 0 (关)",
                       "env": {"AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR": "0"}},
            "R569B3": {"side": "agent", "desc": "执行回灌修复轴 = 3 (剂量档)",
                       "env": {"AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR": "3"}},
        },
        "arm_env_definition_note": "两臂剂量键**都显式落盘**且只有这一个键取值不同 ⇒ 单变量由构造保证; runner 第 0 步机检。"
                                   "其余 env 全臂相同 (R1_CONTRACT / R1_MAX_REPAIR=1 / PUBLIC_SELFCHECK / ROLE_FILE / TRANSCRIPT / WORKSPACE / TAG)。",
        "scope_declaration": {
            "windows": WINS, "window_count": 6,
            "task": "g1 (冻结题面; prompt sha256 与 R559/R560/R563/R565/R566/R567 逐字节相同)",
            "task_prompt_sha256_expected": PROMPT_SHA,
            "binary_sha256_expected": BIN_SHA,
            "hidden_cases": 58,
            "grader_sha256": grader_sha,
            "cross_round_deltas_forbidden": "与 w104..w118 / w119..w124 / w125..w130 / w131..w136 的读数**并列不相减** (新窗, 非同一窗集延续)",
        },
        "criterion_version": "v2 (逐窗并列 + 真值崩窗 unreliable[MARGIN=3] + 配对判据[n>=3, 无窗<=-3, 中位>=-2] + VOID 臂窗单列) "
                             "—— 口径文本取自 docs/external-reference-harness.md §12, 本文件只引用不重定义; **本轮不改判据 v2**",
        "acceptance_rule": {
            "primary": "判据 v2 判决 (eval/rover/r561/verdict_r561.py 装置, adjudicate_r569.py 零逻辑复制复用)",
            "rc": "0 全过 / 1 判据未过 (被测或前提) / 2 器具缺陷 / 3 缺侧或不可判",
            "expected_direction": "**无增益预期** (零产品改动): ①两档配对差若与 R566/R567 同向或更小 ⇒ 剂量档位不是承重变量; "
                                  "②若三窗集 (w119..w142) 方向一致且效应 > 跨窗摆动 ⇒ 单列「剂量档位有平均增益」候选, 仍**不得**作增益宣称 (铁律 11)。",
            "cross_check": "铁律 11 前置器 python3 eval/rover/r507pre/exec_precondition.py --round r569 (两侧产出物独立物化 + 真跑 + 逐用例判对); rc!=0 ⇒ 全部成本/降幅读数标「参考(未可验收)」",
        },
        "extra_prereg_rules_candidate3": {
            "note": "承 R568 补记面; 两条规则**先于本窗集落盘** (防事后挑选)",
            "E1 逐窗回退点名": "对每个臂给出「配对差 <= -3 例」的窗号点名 (逐窗并列, 不与其它窗集相减); 有回退窗 ⇒ 不得宣称「逐窗不回退」",
            "E2 拒收窗排除规则": "若某臂窗满足 rc==8 ∧ cases_total==58 ∧ cases_pass==0 ∧ stage=='public_probe_unmet' ⇒ 记为「交付前自测闸**拒收窗**」"
                                 "(R568 曾称『臂级崩溃窗』; R569-④ 定因: 该窗产物已落盘且 58/58 `stdout_mismatch`, 属**产品 fail-closed 自测闸行使**而非运行级崩溃), "
                                 "该窗从**配对均值**中剔除并**两个数并列报** (含 / 剔), 不作挑选; 剔除规则不得用于改变判据 v2 判决",
            "E3 新实体的判据口径": "拒收窗的剔除**只影响补记面**, 判据 v2 判决 (主判据) 照原样判定, 不改阈值",
        },
        "candidate4": {
            "name": "判定输入指纹 / 命中率双口径复核 (新窗)",
            "exercise_arm": "R569B3",
            "pre_registered_checks": {
                "C4-1 恒等式": "每个中继 dump: prompt_tokens == hit + miss ∧ 0 <= hit <= prompt (违反 >0 ⇒ rc=2 器具/口径缺陷)",
                "C4-2 确定性": "行使臂每窗**第 1 次调用**的 prompt sha8 全窗相同 ∧ transcript 任务/前缀 sha 全窗相同",
                "C4-3 非平凡": "call1 vs call2 的 prompt sha 跨窗**互异** (确定性 ≠ 恒定输出)",
                "C4-4 命中率双口径": "v_all(含冷启动) / v_incr(去冷启动) 逐窗出数; 未上报记哨兵不入比率",
            },
            "rc": "0 全过 / 2 违反 / 3 输入缺失; 未行使 ⇒ 记 honest_boundary, 不改判据",
        },
        "candidate5_gate_clause": {
            "candidate": "R569-⑤ 起手闸振幅余量条款 **加上界** (R568 预注册的下一轮规则)",
            "rule": "MARGIN := min(max(FLOOR=60, prev_swing), ceiling_mb - GATE_MB); REQ = GATE_MB + MARGIN",
            "derivation": "prev_postcheck = eval/rover/r567/gate-postcheck-r567.json (swing_mb=103) ⇒ want=103; "
                          "cap = 本次起手前 3 次采样的 max - 2650 ⇒ MARGIN = min(103, cap) (上界行使时 margin_capped=true)",
            "fail_closed": "cap < FLOOR ⇒ rc=2 (顶棚连下限都装不下, 不静默放行); 派生失败/顶棚 < REQ ⇒ 不起臂",
            "instrument_change_declaration": "关键器改版: eval/rover/r569/gate_margin_r569.py 相对 r567 件在 derive/why/clause/selftest 四处有声明式差异; "
                                             "成对控制由 6 例改为 7 例 (正控 3 + 正控『旧 v1 常量被夹』1 + 负控 3), 断言逐例同时校验 rc **与** margin_capped",
            "controls": {
                "PC": "连续 2 次 preflight_gate --gate-mb REQ ⇒ 期望 PASS ×2",
                "NC_hog": "400MB 占用 ⇒ 期望 GATE_BLOCKED",
                "discriminating_pair": "把内存态压进判别带 [2650, REQ) 后: --gate-mb 2650 ⇒ PASS ∧ --gate-mb REQ ⇒ GATE_BLOCKED; 带内不可达 ⇒ rc=3 如实登记",
            },
        },
        "evidence_scope": {"require": ["%s/%s" % (w, a) for w in WINS for a in ARMS]},
        "preregistered_expectations": {
            "quality": "无增益预期 (零产品改动 ⇒ 只作读数, 不作增益宣称); 三臂同窗配对",
            "cost": "调用数/新算 prompt/completion 三列分列 (禁名义总量)",
            "honest_boundary": "g1 族的 wythoff 失分已三次定因 (产物缺陷); 本轮不修 (未放行) ⇒ 铁律 11 rc=1 可能性高, 不得据此改写判据",
        },
        "notes": "本文件先写后跑 (runner 第 0 步机检: round / 臂集 3 / require 18 / criterion_version v2 / 两臂剂量键集与取值 0 vs 3)。"
                 "判据 v2 口径不在本文件重定义, 只引用 docs/external-reference-harness.md §12。",
    }
    json.dump(pre, io.open(os.path.join(PDIR, "prereg-r569.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[预注册] arms=%s require=%d" % (sorted(pre["arms"]), len(pre["evidence_scope"]["require"])))

    d = json.load(io.open(os.path.join(PDIR, "prereg-r569.json"), encoding="utf-8"))
    assert d["round"] == "R569" and d["written_before_run"] is True
    assert set(d["arms"]) == {"C1", "R569B0", "R569B3"}, sorted(d["arms"])
    assert len(d["evidence_scope"]["require"]) == 18
    assert str(d["criterion_version"]).startswith("v2")
    doses = {a: int(d["arms"][a]["env"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"]) for a in ("R569B0", "R569B3")}
    assert doses == {"R569B0": 0, "R569B3": 3}, doses
    assert not (set(WINS) & set(WINS_PREV)), WINS
    assert len(d["extra_prereg_rules_candidate3"]) >= 4
    print("[机检] 预注册 7 项全过 (dose=%s, wins=%s)" % (doses, WINS))
    return 0


def main():
    os.makedirs(PDIR, exist_ok=True)
    freeze_copy()
    derive_files()
    gate_patch()
    gs = sha(os.path.join(PDIR, "cases", "run_cases_r521.py"))
    rc = prereg(gs)
    # 成对控制自检 (器具改版后必须重跑)
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(PDIR, "gate_margin_r569.py"), "--selftest"],
                       capture_output=True, text=True)
    print("[条款成对控制] rc=%d %s" % (r.returncode, r.stdout.strip()[:600]))
    if r.returncode != 0:
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main())
