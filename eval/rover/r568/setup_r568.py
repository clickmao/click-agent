#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R568 预注册**机取件** (候选③+④) —— 所有数字由冻结件派生, 禁手抄。
零新臂 / 零新窗口 / 零远端 / 零产品源码改动 / 零新增夹具 / 零新增开关。

候选③ 剂量轴并池只读复核: 把已落盘的**逐例矩阵** (percase-matrix-*.json, 判分器对副本判分)
按「臂→剂量」映射并池 = 同题面重复窗池 ⇒ 回答两问:
  (a) 跨窗摆动是「逐例稳定、少数例翻转」还是「逐例弥漫抖动」;
  (b) 剂量档 (0/1/3) 之间是否存在**逐例显著**差异 (若否 ⇒ 如实收窄: 无剂量增益)。
候选④ 起手闸行使: MARGIN 由上一轮**运行中实测振幅** (R567 postcheck swing_mb) 派生 ⇒ REQ = 2650 + MARGIN,
以**既有闸的 --gate-mb** 生效 (零新逻辑进闸), 并做判别带成对控制 + 成对控制自检。

派生源 (全部只读):
  ① eval/rover/*/percase-matrix-*.json  (逐例矩阵; sets 给出 轮→窗口→臂)
  ② <该轮>/prereg-<轮>.json             (臂→env 取值; 缺键记 default)
  ③ <该轮>/bins-<轮>.json 或 prereg.bin_sha256 (二进制 sha)
  ④ eval/rover/r567/gate-postcheck-r567.json (上一轮观测振幅)
输出: eval/rover/r568/prereg-r568.json (written_before_run)
"""
from __future__ import annotations

import glob
import hashlib
import io
import json
import os
import re
import sys

REPO = "/home/agentuser/AgentFramework"
DOSE_KEY = "AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"
OPT_SRC = "src/agent/r1/R1Options.cs"
OUT = os.path.join(REPO, "eval/rover/r568/prereg-r568.json")


def sha256(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def load_json(p):
    return json.load(io.open(p, encoding="utf-8"))


def source_default():
    """产品**源码派生**的默认剂量 (禁手抄; 与 eval 侧命名无关)。

    臂名里的 'B0' 是**执行体侧的标签**, 不等于 env 取值: 某轮 prereg 的 env 写成
    「(unset) = R1Options defaults」 ⇒ 该臂走的是**产品默认档**。默认档取值只许从
    产品源码读 (R469 纪律: 规则常量源码派生 + 记 sha)。
    """
    p = os.path.join(REPO, OPT_SRC)
    txt = io.open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"int\s+MaxExecRepair\s*=\s*(\d+)", txt)
    if not m:
        return None, None
    return int(m.group(1)), sha256(p)


def discover():
    """扫全仓逐例矩阵 ⇒ {round: {wins, arms, path, sha}} (机取, 禁硬编码清单)。"""
    sets = {}
    reg = []
    for p in sorted(glob.glob(os.path.join(REPO, "eval/rover/*/percase-matrix-*.json"))):
        d = load_json(p)
        rel = os.path.relpath(p, REPO)
        reg.append({"path": rel, "sha256": sha256(p)})
        for s in d.get("sets", []):
            rd = s["round"]
            sets.setdefault(rd, {"wins": [], "arms": [], "matrices": [], "grader_sha": set(),
                                 "cases_sha": set()})
            sets[rd]["wins"] += list(s["wins"])
            sets[rd]["arms"] += list(s["arms"])
            sets[rd]["matrices"].append(rel)
            sets[rd]["grader_sha"].add(d["grader"]["sha256"])
            sets[rd]["cases_sha"].add(d["cases"]["sha256"])
    return sets, reg


def arm_dose(round_name, arm, default):
    """由该轮 prereg 的臂 env 派生剂量。
    env 显式给出键 ⇒ 用其取值; 未给键 (含 '(unset)' 形态) ⇒ 用**源码派生**的默认档。
    返回 (dose, 形态标签)。形态标签进登记表, 便于读者区分「显式 0」与「未设键的默认档」。
    """
    p = os.path.join(REPO, "eval/rover", round_name.lower(), "prereg-%s.json" % round_name.lower())
    if not os.path.isfile(p):
        return None, "no_prereg"
    d = load_json(p)
    a = (d.get("arms") or {}).get(arm)
    if not isinstance(a, dict):
        return None, "no_arm"
    env = a.get("env") or {}
    if DOSE_KEY in env:
        raw = env[DOSE_KEY]
        try:
            return int(str(raw).strip()), "env_explicit"
        except Exception:  # noqa: BLE001
            return None, "env_unparsable:%s" % raw
    return default, "product_default"


def arm_bin_sha(round_name, arm):
    rd = round_name.lower()
    b = os.path.join(REPO, "eval/rover", rd, "bins-%s.json" % rd)
    if os.path.isfile(b):
        v = (load_json(b).get("bin_all_arms") or {}).get("sha256")
        if v:
            return v
    p = os.path.join(REPO, "eval/rover", rd, "prereg-%s.json" % rd)
    if os.path.isfile(p):
        a = (load_json(p).get("arms") or {}).get(arm)
        if isinstance(a, dict):
            return a.get("bin_sha256")
    return None


def main():
    sets, reg = discover()
    if not sets:
        print("NO_MATRICES ⇒ rc=3")
        return 3
    default, opt_sha = source_default()
    if default is None:
        print("SOURCE_DEFAULT_UNREADABLE ⇒ rc=3 (fail-closed: 默认档取值必须源码派生)")
        return 3
    rounds = sorted(sets, key=lambda r: int(r[1:]))
    all_windows, dose_of_arm, dose_shape, sha_of_arm = {}, {}, {}, {}
    for r in rounds:
        for w in sets[r]["wins"]:
            all_windows.setdefault(w, {"round": r, "arms": []})
            all_windows[w]["arms"] = sorted(set(all_windows[w]["arms"]) | set(sets[r]["arms"]))
        for a in sets[r]["arms"]:
            if a == "C1":
                dose_of_arm[a] = None
                dose_shape[a] = "external_truth"
                sha_of_arm[a] = arm_bin_sha(r, a)
                continue
            dose, shape = arm_dose(r, a, default)
            dose_of_arm[a] = dose
            dose_shape[a] = shape
            sha_of_arm[a] = arm_bin_sha(r, a)
    dose_windows = {}
    for a, dose in dose_of_arm.items():
        if a == "C1" or dose is None:
            continue
        for r in rounds:
            if a in sets[r]["arms"]:
                dose_windows.setdefault(dose, set())
                dose_windows[dose] |= set(sets[r]["wins"])
    dose_windows = {d: sorted(w) for d, w in sorted(dose_windows.items())}
    shape_counts = {}
    for a, s in dose_shape.items():
        if a == "C1":
            continue
        shape_counts.setdefault(s, []).append(a)
    gate = os.path.join(REPO, "eval/rover/r567/gate-postcheck-r567.json")
    gd = load_json(gate) if os.path.isfile(gate) else {}
    margin = max(60.0, float(gd.get("swing_mb") or 0))
    pre = {
        "round": "R568",
        "written_before_run": True,
        "author": "cron-agent (60min tick, 2026-09-19)",
        "mode": "readonly_pooled_review + gate_clause_exercise (零新臂 / 零新窗口 / 零远端)",
        "claim": ("**只读并池轮**: ① 候选③ 剂量轴并池只读复核 —— 把已落盘的逐例矩阵按臂→剂量并池 "
                  "(同题面重复窗池), 回答「跨窗摆动是否逐例弥漫」与「剂量档 0/1/3 是否有逐例显著差异」; "
                  "② 候选④ 起手闸 MARGIN=上一轮实测振幅 (R567 postcheck) ⇒ REQ 派生并**真实行使** "
                  "(既有闸 --gate-mb + 判别带成对控制 + 成对控制自检)。"
                  "零产品源码改动 / 零新增夹具 / 零新增开关 (用户令 2026-09-18「开工, 不许新增夹具和额外开发了」)。"),
        "one_time_context": "用户令 2026-09-19「继续下一轮」⇒ 按 R567 收口登记的两条零开发候选执行; 不重开器具/文档线。",
        "candidates_ledger": {
            "R568-① 剂量轴并池只读复核 (R559∪R560∪R563∪R565∪R566∪R567)": "做 —— 承重候选 (纯只读)",
            "R568-② 起手闸 REQ 行使 (零开发)": "做 —— MARGIN 由 R567 postcheck 振幅派生",
            "R568-③ 契约加厚 v3 / 产物落点自验": "未做 —— 须动契约/产品分支 ⇒ 未放行",
            "R568-④ 交付闸/停止条件 (rc=5/8)": "未做 —— 新增产品分支 ⇒ 未放行",
            "R568-⑤ exp1 backlog 器具类剩余候选": "未做 —— 与用户 2026-09-17 方向逆转 (器具/登记判封存) 冲突 ⇒ 只登记",
        },
        "derived_from": {
            "matrices": reg,
            "rounds": rounds,
            "windows_per_round": {r: sets[r]["wins"] for r in rounds},
            "arms_per_round": {r: sets[r]["arms"] for r in rounds},
            "grader_sha_set": sorted({s for r in rounds for s in sets[r]["grader_sha"]}),
            "cases_sha_set": sorted({s for r in rounds for s in sets[r]["cases_sha"]}),
            "arm_dose": dose_of_arm,
            "arm_dose_shape": dose_shape,
            "arm_bin_sha": sha_of_arm,
            "dose_window_counts": {d: len(w) for d, w in dose_windows.items()},
            "dose_windows": dose_windows,
            "all_windows": sorted(all_windows),
            "all_windows_n": len(all_windows),
            "source_default": {"file": OPT_SRC, "sha256": opt_sha,
                               "max_exec_repair_default": default,
                               "why": ("臂名里的 'B0' 是执行体侧标签, 不等于 env 取值: env 未给键的轮次走的是"
                                       "**产品默认档**; 该取值只许从产品源码派生 (本文件机械读出) ⇒ "
                                       "把默认档记成 0 会把该窗池错并到剂量 0")},
        },
        "join_rules": [
            "P1 池化合法性: 全部矩阵 grader_sha 唯一 ∧ cases_sha 唯一 ∧ 全部 agent 臂的二进制 sha 唯一 ∧ "
            "矩阵 sha 与该登记表逐条相符; 任一不符 ⇒ rc=3 (输入/器具缺陷, 不出判决)",
            "臂→剂量映射由各轮 prereg 的 env 机取 (env 未给键 ⇒ 取**源码派生**的产品默认档; 禁手抄); "
            "C1 = 外部真值 (codex), 无剂量、不入剂量比较",
            "跨轮并池的前提是「同题面 ∧ 同判分器 ∧ 同二进制」逐条机检通过 (本登记表 derived_from 即证据)",
        ],
        "criteria": {
            "P2 逐例稳定 (dose0 池 n=%d / dose1 n=%d / dose3 n=%d 窗): 各池混合例数 <= 6"
            % (len(dose_windows.get("0", [])), len(dose_windows.get("1", [])), len(dose_windows.get("3", []))):
                "混合例 = 在同一剂量池内既有 PASS 又有 FAIL 的用例 (#idx); 阈值 6 ≈ 58 例的 10%; "
                "超阈值 ⇒ 「跨窗摆动逐例弥漫」, 逐窗单点读数不得作能力结论 (承 R413/R417 纪律)",
            "P3 剂量无显著差: 逐例 Fisher 精确双侧 p<0.05 的例数 (0 vs 3 与 0 vs 1) 均 <= 2": 
                "每例 = 2×2 表 (通过数/失败数 × 两剂量); 效应分辨率下限 (Δ_min) 由同一表反解并落盘 —— "
                "阈值必须大于该下限, 否则判据在数学上放行噪声 (R404 形态)",
            "P4 失分归属 (dose0 池 × codex 池 n=%d 窗): 同败例集 (两侧失败率均 >=0.5) 单独计数并列名" % len(all_windows):
                "同败例多 ⇒ 先疑夹具/契约 (R512 形态: 两侧失败集合逐字相同); 仅我方失败的例 ⇒ 能力面; 两类分列不混算",
            "P0 非平凡 (成对判据另一半): 族级通过率集合大小 >= 2 ∧ codex 与 agent 的逐例全败集合不相同":
                "恒定的逐例读数 = 判据退化 (与「确定性 ∧ 非平凡」同族)",
        },
        "negative_controls": {
            "NC1 sha 失配": "把任一矩阵的 grader/cases sha 改成异值 ⇒ 判据器必须 rc=3 (fail-closed, 不出判决)",
            "NC2 稳定性判据有牙": "合成注入 1 例「窗间翻转」⇒ 混合例数必须 +1 并反映在读数里",
            "NC3 剂量判据有牙": "合成注入 1 例「dose0 全过 / dose3 全败」⇒ 敏感性例数必须 +1 且 rc=2",
            "NC4 闸判别力": "内存态压进判别带 [2650, REQ) ⇒ 基础门槛 PASS ∧ 条款 GATE_BLOCKED (真判别行使)",
        },
        "gate_clause": {
            "source": "eval/rover/r567/gate_margin_r567.py (既有器具, 零改动)",
            "prev_postcheck": "eval/rover/r567/gate-postcheck-r567.json",
            "prev_swing_mb": gd.get("swing_mb"),
            "margin_mb": margin,
            "required_mb": 2650 + margin,
            "applied_via": "既有闸 eval/rover/r483/preflight_gate.py --gate-mb",
            "honest_note": ("R567 运行窗口内实测 min=%s MB 低于本轮派生 REQ=%s MB ⇒ 若本轮起手读数也低于 REQ, "
                            "闸应 BLOCKED 而非放行 (fail-closed); 该读数本身就是条款判别力的证据"
                            % (gd.get("in_min_mb"), 2650 + margin)),
        },
        "exclusions": {
            "产品源码": "零改动", "夹具/开关": "零新增", "远端": "零调用", "新臂/新窗口": "零 (纯复用冻结件)",
        },
        "write_disclosure": ("判据主体 (criteria / negative_controls / gate_clause) 在**开跑前**落盘; "
                             "amendments 内各条为**跑后**自捕登记 (派生缺陷 / 阈值标定), 判据文本**未被改写**, "
                             "本轮判决按原判据出 (禁事后调阈值)。"),
        "amendments": [
            {"stage": "v1→v2 (机取修正, 判据文本零改动)",
             "what": "派生表 v1 未把外部真值臂 C1 排除出剂量映射 ⇒ 剂量 1 池混入 codex 行 (臂窗 24 != 12, "
                     "例窗 1392 != 696)。**算术自检抓到** (臂窗数 != 窗数 × 该剂量臂数)。"
                     "修法 = C1 记 dose=None / shape=external_truth; 池只统计**该剂量自己的臂**。"
                     "v1 读数 (dose0 例窗 2784 = 48 臂窗) 作废并按器具缺陷登记, 不写入结论。",
             "criteria_unchanged": True},
            {"stage": "P2 阈值标定 (自捕, 事后)",
             "what": "P2「各池混合例 <= 6」在池规模/失败率下**数学上不相容**: 均匀失败模型下全过例数 "
                     "≈ 58·(1−q)^n (dose0: q≈0.15, n=27 ⇒ 期望 ~54 例全过 ⇒ 混合例期望 ~4) —— 但实测"
                     "全过例=0 (z≈−27), 即**过分散**: 失败几乎覆盖每一例。阈值形态应是「观测全过例数 vs "
                     "均匀模型期望 ±2σ」而非固定例数。预注册判决**照原样保留**, 修正形态入 checks_posthoc",
             "criteria_unchanged": False,
             "why_not_rewritten": "禁事后调阈值; 本轮按原判据判 (rc=2), 修正形态只作下一轮预注册输入"},
        ],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(pre, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: pre["derived_from"][k] for k in
                      ("rounds", "dose_window_counts", "grader_sha_set", "cases_sha_set")},
                     ensure_ascii=False))
    print("arm_dose:", json.dumps({k: v for k, v in sorted(dose_of_arm.items())}, ensure_ascii=False))
    print("arm_bin_sha set:", sorted({v for v in sha_of_arm.values() if v}))
    print("gate: prev_swing=%s margin=%s REQ=%s" % (gd.get("swing_mb"), margin, 2650 + margin))
    print("WROTE", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
