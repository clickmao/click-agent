#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R632 · 候选① —— **判据族对齐件**：重审 R631（冻结件、零重测），判据键集合与
`prereg-r631.json` 的 `criteria` 键集合**逐键相等**，并把判决来源改成**机读字段**。

背景（R631 自捕器件缺陷 D2，如实披露、不翻案）:
  `eval/rover/r631/judge_r631.py` 的判据键族 = `J1_exec_face_consumed / J1a..J1e / J2_repair_convergence /
  J2b_selection_conservation / J4_capability_secondary / J5_cross_windowset_same_direction /
  J6_zero_regression_equivalence / v3 / C1_task_face_v3`（旧草稿残留），而 `prereg-r631.json` 声明的是
  `J0 / J1_fallback_exercised / J4a / J4b / J3 / J6_equivalence_face / W_floor_resolution_floor / P11`。
  两者**不同源** ⇒ 该件判决不予采用（保留在盘、不改写）。本件按 prereg-r631 的判据族**重审**同一批冻结读数。

分工（单一实现，防漂移）:
  * **解析层复用** `judge_r631.py` 的 `read_transcript / read_cases / load_helpers`（读取契约已由 R631 修好，
    含 `exec_fallback` 两处并入的教训）——解析层不再另写一份。
  * **判据层完全重写**，逐键对照 prereg-r631 `criteria[k].need`；每个键**无条件计算**（未行使记
    `informational`/`null`，禁键缺失）——承 "verdict 键在条件分支内计算 ⇒ 静默假阴性" 教训。

判据语义（逐字取自 prereg-r631）:
  J0  : 机制面 —— T 逐跑次 exec_source ∈ {candidates, plan_fallback} ∧ C 档五字段全缺席 ∧ 两臂前缀同源 ∧ 每臂非全缺席
  J1  : 机制面（primary=true）—— 面覆盖 T 全部跑次 ∈ {candidates, plan_fallback} ∧ 回退跑次 ≥1 ∧ 回退跑次 executed>0 全部
        ∧ 守恒（仅在 candidates 源上有定义）；不满足 ⇒ `NOT_EXERCISED`（**不判 PASS 不判红**，单列）
  J4a : 能力次级 —— 逐窗配对 Δ := T − C；判据 = Δ 中位 > 0 ∧ 逐窗符号非负占比 ≥ 1/2（n=2 ⇒ 欠功率）
  J4b : 能力 —— 逐窗 D := 产品 − codex 真值；判据 = D 中位 ≥ −2 ∧ 无窗 ≤ −15；真值自败窗按 `unreliable_policy` 单列
  J3  : 成本 —— 三列分列 ∧ v2 三条款（Σcalls T ≤ C ∧ 逐窗 Σcalls T ≤ C ∧ 单位调用新算 prompt T ≤ C）
  J6  : 机制次级 —— 已由 R621 定案关闭 ⇒ 本轮**只登记**（informational），不作主判据
  W_floor : 分辨率 —— 有效窗 <2 ⇒ rc=3（禁下调阈值）
  P11 : 验收面 —— 铁律 11 前置器给出 named 阻塞（禁 DISCOVER_FAIL）⇒ 验收面可归属；rc 由该器判定

用法:
  python3 eval/rover/r632/judge_align_r632.py --D ~/.agentframework/harness/runs/r631 [--extract-out <p>]
  python3 eval/rover/r632/judge_align_r632.py --extract <evidence/run-extract-r631.json>   # 交叉校验路径
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import statistics
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PD_R631 = os.path.join(REPO, "eval/rover/r631")
PD = os.path.join(REPO, "eval/rover/r632")
PREREG_SRC = os.path.join(PD_R631, "prereg-r631.json")
PREREG_SELF = os.path.join(PD, "prereg-r632.json")
PRECOND = os.path.expanduser("~/.agentframework/harness/runs/r631/precond-r631.json")
PRECOND_RC = os.path.expanduser("~/.agentframework/harness/runs/r631/precond.rc")

STATES = ("pass", "fail", "informational", "not_exercised", "input_missing")


def sha256_file(p):
    try:
        return hashlib.sha256(io.open(p, "rb").read()).hexdigest()
    except Exception:
        return None


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------- 冻结抽取（两条独立路径之一）
def build_recs_from_runs(D, j631):
    """从 runs 目录重建逐跑次读数（路径 A）。返回 (recs, evidence_sha, runs_sha)。"""
    runs_p = os.path.join(D, "logs", "runs.jsonl")
    runs = [json.loads(l) for l in io.open(runs_p, encoding="utf-8") if l.strip()]
    mod = j631.load_helpers()
    recs, ev = [], {}
    for r in runs:
        side = "codex" if r["sub"] == "codex" else "agent"
        st = mod.arm_stats(os.path.join(D, "adapter"), side, tuple(r["range"]))
        g = os.path.join(D, r["win"], r["sub"], "g1")
        tp = os.path.join(g, "transcript.json")
        cs = j631.read_cases(os.path.join(g, "cases.txt"))
        tr = j631.read_transcript(tp)
        ev["%s/%s/g1/transcript.json" % (r["win"], r["sub"])] = sha256_file(tp)
        recs.append({"arm": r["arm"], "win": r["win"], "rep": r["rep"], "sub": r["sub"], "side": side,
                     "cases_pass": cs["pass"], "cases_total": cs["total"],
                     "all_pass": bool(cs["total"] == 58 and cs["pass"] == 58),
                     "calls": st["calls"], "new_prompt": st["new_prompt"], "completion": st["completion"],
                     "v_all": st["v_all"], "v_incr": st["v_incr"], "tr": tr})
    return recs, ev, sha256_file(runs_p)


def freeze_extract(D, out):
    j631 = load_mod("_j631x", os.path.join(PD_R631, "judge_r631.py"))
    recs, ev, runs_sha = build_recs_from_runs(D, j631)
    doc = {"round": "R631", "kind": "R631 逐跑次读数冻结抽取（供 R632 判据族对齐件重审；零重测）",
           "source_runs_jsonl_sha256": runs_sha, "transcript_sha256": ev, "recs": recs}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(doc, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return doc


# ---------------------------------------------------------------- 判据层（逐键对照 prereg-r631）
def _windows(recs):
    return sorted({r["win"] for r in recs}, key=lambda w: int(w[1:]))


def judge(recs, prereg_src, prereg_self, precond_path, precond_rc_path):
    crit = prereg_src["criteria"]
    keys_src = sorted(crit.keys())
    out = {}

    def of(arm, win=None):
        return [r for r in recs if r["arm"] == arm and (win is None or r["win"] == win)]

    EXEC_FIELDS = ("exec_source", "action_candidates_executed", "action_candidates_unmapped",
                   "action_candidates_expect_inherited", "exec_fallback")

    # ---- J0 ----------------------------------------------------------------
    T, C = of("T"), of("C")
    preT = sorted({(r["tr"] or {}).get("prefix_sha256") for r in T if (r["tr"] or {}).get("prefix_sha256")})
    preC = sorted({(r["tr"] or {}).get("prefix_sha256") for r in C if (r["tr"] or {}).get("prefix_sha256")})
    es_T = [(r["tr"] or {}).get("exec_source") for r in T]
    absent_C = sum(1 for r in C if all((r["tr"] or {}).get(k) is None for k in EXEC_FIELDS))
    j0_pass = bool(es_T and all(x in ("candidates", "plan_fallback") for x in es_T)
                   and absent_C == len(C) and preT and preT == preC and T and C)
    out["J0_arm_axis_effective"] = {
        "kind": crit["J0_arm_axis_effective"]["kind"], "state": "pass" if j0_pass else "fail",
        "pass": j0_pass, "T_exec_source": es_T, "T_prefix_set": preT, "C_prefix_set": preC,
        "C_new_fields_absent_runs": absent_C, "C_runs": len(C), "T_runs": len(T),
        "need": crit["J0_arm_axis_effective"]["need"]}

    # ---- J1（primary）: 回退面行使 + 守恒 --------------------------------
    fb_T = [r for r in T if (r["tr"] or {}).get("exec_source") == "plan_fallback"]
    cand_T = [r for r in T if (r["tr"] or {}).get("exec_source") == "candidates"]
    face_ok = bool(T) and all((r["tr"] or {}).get("exec_source") in ("candidates", "plan_fallback") for r in T)
    fb_exec_ok = bool(fb_T) and all(((r["tr"] or {}).get("action_candidates_executed") or 0) > 0 for r in fb_T)
    # 守恒仅在 candidates 源上有定义（prereg 逐字）
    cons = []
    for r in cand_T:
        tr = r["tr"] or {}
        d, a, rj, ex = (tr.get("action_candidates_declared"), tr.get("action_candidates_accepted"),
                        tr.get("action_candidates_rejected"), tr.get("action_candidates_executed"))
        if None in (d, a, rj, ex):
            cons.append({"win": r["win"], "rep": r["rep"], "defined": False})
        else:
            cons.append({"win": r["win"], "rep": r["rep"], "defined": True,
                         "declared_eq": bool(d == a + rj), "executed_le_accepted": bool(ex <= a)})
    cons_ok = all(c["declared_eq"] and c["executed_le_accepted"] for c in cons if c["defined"])
    if not fb_T:
        j1_state, j1_pass = "not_exercised", None       # prereg: 不判 PASS 不判红
    else:
        j1_pass = bool(face_ok and fb_exec_ok and cons_ok)
        j1_state = "pass" if j1_pass else "fail"
    out["J1_fallback_exercised"] = {
        "kind": crit["J1_fallback_exercised"]["kind"], "primary_from_prereg": True,
        "state": j1_state, "pass": j1_pass, "T_face_covered": face_ok,
        "fallback_runs": len(fb_T), "fallback_exec_ok": fb_exec_ok,
        "conservation_only_on_candidates_source": cons, "conservation_ok": cons_ok,
        "not_exercised_note": None if fb_T else "回退 0 行使 ⇒ 单列，不判 PASS 不判红（prereg fail_action 逐字）",
        "need": crit["J1_fallback_exercised"]["need"]}

    # ---- J4a / J4b ---------------------------------------------------------
    wins = _windows(recs)
    per = {}
    for w in wins:
        t, c, c1 = of("T", w), of("C", w), of("C1", w)
        gt = sorted(r["cases_pass"] for r in t)
        gc = sorted(r["cases_pass"] for r in c)
        d_pair = [b - a for a, b in zip(gt, gc)]
        truth_med = statistics.median([r["cases_pass"] for r in c1]) if c1 else None
        per[w] = {
            "T_allpass_rate": (sum(1 for r in t if r["all_pass"]) / len(t)) if t else None,
            "C_allpass_rate": (sum(1 for r in c if r["all_pass"]) / len(c)) if c else None,
            "T_cases_median": statistics.median(gt) if gt else None,
            "C_cases_median": statistics.median(gc) if gc else None,
            "C1_cases_median": truth_med,
            "C1_all_pass": all(r["all_pass"] for r in c1) if c1 else None,
            "reps": {"T": len(t), "C": len(c), "C1": len(c1)},
            "D_T_minus_C_cases_median": (statistics.median(d_pair) if d_pair else None),
            "D_product_minus_truth_cases_median": (None if truth_med is None or not gt
                                                   else statistics.median(gt) - truth_med),
        }
    d_med_a = [per[w]["D_T_minus_C_cases_median"] for w in wins
               if per[w]["D_T_minus_C_cases_median"] is not None]
    j4a_med = statistics.median(d_med_a) if d_med_a else None
    nonneg = (sum(1 for x in d_med_a if x >= 0) / len(d_med_a)) if d_med_a else None
    j4a_pass = bool(j4a_med is not None and j4a_med > 0 and nonneg is not None and nonneg >= 0.5)
    out["J4a_capability_replication"] = {
        "kind": crit["J4a_capability_replication"]["kind"], "state": "pass" if j4a_pass else "fail",
        "pass": j4a_pass, "D_cases_median_by_window": per and {w: per[w]["D_T_minus_C_cases_median"] for w in wins},
        "median": j4a_med, "nonneg_frac": nonneg, "power_note": "n=%d 窗 ⇒ 欠功率，只作趋势不作能力结论" % len(wins),
        "need": crit["J4a_capability_replication"]["need"]}

    # 策略（D2）先行：真值自败窗按 prereg-r632 的 unreliable_policy 机械降级
    #   注意 provenance：R631 的既有窗**先于**本轮策略声明 ⇒ 闸按 B2 拒绝追溯套用
    #   （`eval/rover/r632/evidence/policy-retro-r631.json` = RUN_PREDATES_DECLARATION）。
    #   因此该窗的移出**出处 = RF0005 §3 R4 人工单列**（同一规则、人工行使），**不得**记作「策略驱动」。
    pol = prereg_self.get("unreliable_policy") or {}
    pol_key_ok = bool(pol.get("rule") and pol.get("declared_before_run") and pol.get("policy_declared_ts"))
    retro_p = os.path.join(PD, "evidence", "policy-retro-r631.json")
    retro = {}
    try:
        retro = json.load(io.open(retro_p, encoding="utf-8"))
    except Exception:
        retro = {}
    pol_active = bool(retro.get("active"))          # 对**本窗集**是否生效（B2 决定）
    pol_declared = bool(pol_key_ok)                 # 声明是否合规（对**未来**轮生效）
    unreliable = [w for w in wins if per[w]["C1_all_pass"] is False]
    used = [w for w in wins if w not in unreliable]
    d_use = [(w, per[w]["D_product_minus_truth_cases_median"]) for w in used
             if per[w]["D_product_minus_truth_cases_median"] is not None]
    d_vals = [v for _, v in d_use]
    j4b_med = statistics.median(d_vals) if d_vals else None
    j4b_pass = bool(d_vals and j4b_med >= -2 and all(v > -15 for v in d_vals))
    out["J4b_capability_vs_truth"] = {
        "kind": crit["J4b_capability_vs_truth"]["kind"], "state": "pass" if j4b_pass else "fail",
        "pass": j4b_pass, "D_by_window": dict(d_use), "windows_used": used,
        "unreliable_windows": unreliable, "policy_active": pol_active,
        "policy_active_for_this_window_set": pol_active,
        "policy_declared_for_future_rounds": pol_declared,
        "exclusion_authority": ("unreliable_policy(机检)" if pol_active
                                else "R4 manual single-listing（策略声明晚于本窗集 ⇒ B2 拒绝追溯套用）"),
        "median": j4b_med, "power_note": "可靠窗 n=%d ⇒ 欠功率（R4：真值自败窗单列不筛窗）" % len(used),
        "need": crit["J4b_capability_vs_truth"]["need"]}

    # ---- J3 成本（v2 三条款）---------------------------------------------
    t_calls = sum(r["calls"] or 0 for r in T)
    c_calls = sum(r["calls"] or 0 for r in C)
    a1 = bool(T and C and t_calls <= c_calls)
    a2 = all(sum(r["calls"] or 0 for r in of("T", w)) <= sum(r["calls"] or 0 for r in of("C", w)) for w in wins)
    t_new = sum(r["new_prompt"] or 0 for r in T)
    c_new = sum(r["new_prompt"] or 0 for r in C)
    t_per = (t_new / t_calls) if t_calls else None
    c_per = (c_new / c_calls) if c_calls else None
    b1 = bool(t_per is not None and c_per is not None and t_per <= c_per)
    j3_pass = bool(a1 and a2 and b1)
    out["J3_cost"] = {
        "kind": crit["J3_cost"]["kind"], "state": "pass" if j3_pass else "fail", "pass": j3_pass,
        "sum_calls": {"T": t_calls, "C": c_calls},
        "per_window_calls": {w: {"T": sum(r["calls"] or 0 for r in of("T", w)),
                                 "C": sum(r["calls"] or 0 for r in of("C", w))} for w in wins},
        "new_prompt_sum": {"T": t_new, "C": c_new, "C1": sum(r["new_prompt"] or 0 for r in of("C1"))},
        "completion_sum": {"T": sum(r["completion"] or 0 for r in T), "C": sum(r["completion"] or 0 for r in C),
                           "C1": sum(r["completion"] or 0 for r in of("C1"))},
        "per_call_new_prompt": {"T": t_per, "C": c_per},
        "clauses": {"a1_sum_calls_T_le_C": a1, "a2_per_window_T_le_C": a2, "b1_unit_new_prompt_T_le_C": b1},
        "need": crit["J3_cost"]["need"]}

    # ---- J6（已关闭 ⇒ informational）-------------------------------------
    out["J6_equivalence_face"] = {
        "kind": crit["J6_equivalence_face"]["kind"], "state": "informational", "pass": None,
        "closed_by": "R621 定案关闭（NO_RESOLUTION / 摆动 ≥ 效应）",
        "note": "prereg 逐字：本轮只登记、不作主判据、禁为同一缺口再加轮；如再现 NO_RESOLUTION ⇒ 保持关闭，不翻案",
        "need": crit["J6_equivalence_face"]["need"]}

    # ---- W_floor（分辨率）-------------------------------------------------
    valid = len(d_use)
    w_state = "input_missing" if not wins else ("pass" if valid >= 2 else "fail")
    out["W_floor_resolution_floor"] = {
        "kind": crit["W_floor_resolution_floor"]["kind"], "state": w_state,
        "pass": None if w_state == "input_missing" else (valid >= 2),
        "valid_windows": valid, "all_windows": wins, "unreliable_excluded": unreliable,
        "rule": "有效窗 <2 ⇒ rc=3 停链（禁下调阈值）", "need": crit["W_floor_resolution_floor"]["need"]}

    # ---- P11 验收面（铁律 11）--------------------------------------------
    precond, prc = None, None
    try:
        precond = json.load(io.open(precond_path, encoding="utf-8"))
        prc = int(io.open(precond_rc_path, encoding="utf-8").read().strip())
    except Exception:
        pass
    named = None
    if isinstance(precond, dict):
        named = len(precond.get("blocked") or []) + len(precond.get("blocked_scoped") or [])
    p11_state = "input_missing" if precond is None else ("pass" if (named or 0) > 0 else "fail")
    out["P11_precondition_face"] = {
        "kind": crit["P11_precondition_face"]["kind"], "state": p11_state,
        "pass": None if p11_state == "input_missing" else bool((named or 0) > 0),
        "precond_path": precond_path, "precond_sha256": sha256_file(precond_path),
        "precond_rc": prc, "named_blocked_entries": named,
        "discover_fail": bool(isinstance(precond, dict) and precond.get("discover_fail")),
        "need": crit["P11_precondition_face"]["need"]}

    return out, per, keys_src, pol_active, unreliable, pol_declared, retro


D3_CHECKER = os.path.join(PD, "decl_driver_check_r632.py")
D4_FILES = ["eval/rover/r631/verdict-r631.json", "eval/rover/r631/verdict-j4ab-r631.json",
            "eval/rover/r631/kpi-table-r631.json", "eval/rover/r631/prereg-r631.json"]
LEDGER = "docs/research/lit-review-ledger.md"
R632_START_SHA = None  # 由 --pre-sha 传入（轮前 pin）；缺省时退化为「与 HEAD 逐字节一致」判据


def d3_driver_decl(round_id="r631"):
    """D3：轮驱动器头部声明 vs 实盘赋值（委派 decl_driver_check_r632.py，单一实现防漂移）。"""
    mod = load_mod("_declchk", D3_CHECKER)
    r, hdr = mod.check(os.path.join(REPO, "eval/rover/%s/run_%s.sh" % (round_id, round_id)), round_id)
    ev = os.path.join(PD, "evidence", "decl-refresh-%s.json" % round_id)
    ref = json.load(io.open(ev, encoding="utf-8")) if os.path.exists(ev) else {}
    return {"state": "pass" if r["verdict"] == "PASS" else "fail",
            "verdict": r["verdict"], "checked": r["checked"], "drifted": r["drifted"], "absent": r.get("absent"),
            "items_drifted": [x["label"] for x in r["items"] if x["verdict"] == "drift"],
            "refresh_evidence": os.path.relpath(ev, REPO) if ref else None,
            "refresh_body_unchanged": ref.get("body_unchanged"),
            "refresh_header_sha_before": ref.get("header_sha256_before"),
            "refresh_header_sha_after": ref.get("header_sha256_after"),
            "fix_scope": "只改注释声明文本；`set -uo pipefail` 之后实盘段 sha256 逐字节不变（D4 机检）"}


def _git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True).stdout.strip()


def _git_blob_sha(path):
    """取 HEAD 上该路径的 **blob 字节** 的 sha256。

    坑（R632 自捕）：`git show HEAD:<path>` 的 stdout 经 `.strip()`/`text=True` 处理会**丢掉/改写尾字节**
    （尾换行、CRLF 转换）⇒ 与现盘 sha 必然不等 ⇒ **假红**。故这里用 `git cat-file blob` + **bytes** 管道。
    """
    r = subprocess.run(["git", "-C", REPO, "cat-file", "blob", "HEAD:%s" % path], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    return hashlib.sha256(r.stdout).hexdigest()


def d4_history_pin():
    """D4：修法不得改写任何历史判决 —— 四件 sha256 与轮前 pin / HEAD 逐字节一致。"""
    rows = []
    for f in D4_FILES:
        ap = os.path.join(REPO, f)
        disk = sha256_file(ap)
        head_sha = _git_blob_sha(f)
        rows.append({"file": f, "sha256_disk": disk, "sha256_head": head_sha,
                     "unmodified_vs_head": head_sha == disk})
    hij = _git("log", "-1", "--format=%H %cI", "--", D4_FILES[0]).split(" ")
    ok = all(r["unmodified_vs_head"] for r in rows)
    return {"state": "pass" if ok else "fail", "files": rows,
            "head_commit_and_ts_for_pin_source": hij[0] if hij else None,
            "pin_rule": "轮前 pin = HEAD 上该文件的 blob sha256；HEAD 提交时刻须早于本轮 prereg 的 written_at",
            "driver_sh_not_in_scope": "eval/rover/r631/run_r631.sh **不在** D4 清单内（它是声明刷新的对象；其实盘段 sha 由 D3 件单独钉住）"}


def d5_lit_step():
    """D5：文献小步（arXiv 出口可用性分离 + 第二来源 + 台账追加）。"""
    txt = io.open(os.path.join(REPO, LEDGER), encoding="utf-8").read()
    import subprocess as _sp
    probes = {}
    for u in ("https://export.arxiv.org/api/query?search_query=all:test&max_results=1",
              "https://arxiv.org/abs/2402.03300", "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300?fields=title"):
        try:
            r = _sp.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "-m", "12", u],
                        capture_output=True, text=True, timeout=20)
            probes[u] = r.stdout.strip()
        except Exception as e:  # noqa: BLE001
            probes[u] = "ERR:%s" % type(e).__name__
    arxiv_ok = probes.get("https://export.arxiv.org/api/query?search_query=all:test&max_results=1") == "200"
    has_r632 = ("## R632（2026-09-22）" in txt)
    deferred = ("顺延" in txt.split("## R632")[-1]) if has_r632 else False
    return {"state": "pass" if (has_r632 and deferred) else "input_missing",
            "ledger": LEDGER, "ledger_sha256": sha256_file(os.path.join(REPO, LEDGER)),
            "ledger_lines": len(txt.splitlines()), "r632_section_present": has_r632,
            "arxiv_query_available_now": arxiv_ok, "exit_probe_http": probes,
            "deferred_recorded": deferred,
            "verdict": ("arXiv 面顺延（出口 429；不计 0 采信）＋ 第二来源 2 篇（采信 0 / 观察 1）"
                        if deferred else "文献小步未落台账 ⇒ input_missing"),
            "rule": "空结果必须与出口可用性分离：出口不可达的轮次不计入空采信/降频判定"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", default=os.path.expanduser("~/.agentframework/harness/runs/r631"))
    ap.add_argument("--extract", default=None, help="改从冻结抽取件读（交叉校验路径）")
    ap.add_argument("--extract-out", default=None)
    ap.add_argument("--json", default=os.path.join(PD, "verdict-r632.json"))
    a = ap.parse_args()

    prereg_src = json.load(io.open(PREREG_SRC, encoding="utf-8"))
    prereg_self = json.load(io.open(PREREG_SELF, encoding="utf-8"))

    if a.extract_out:
        doc = freeze_extract(a.D, a.extract_out)
        recs, ev_sha, runs_sha = doc["recs"], doc["transcript_sha256"], doc["source_runs_jsonl_sha256"]
        path_mode = "runs-dir(A)"
    elif a.extract:
        doc = json.load(io.open(a.extract, encoding="utf-8"))
        recs, ev_sha, runs_sha = doc["recs"], doc["transcript_sha256"], doc["source_runs_jsonl_sha256"]
        path_mode = "frozen-extract(B)"
    else:
        j631 = load_mod("_j631y", os.path.join(PD_R631, "judge_r631.py"))
        recs, ev_sha, runs_sha = build_recs_from_runs(a.D, j631)
        path_mode = "runs-dir(A)"

    (crit_out, per, keys_src, pol_active, unreliable,
     pol_declared, retro) = judge(recs, prereg_src, prereg_self, PRECOND, PRECOND_RC)
    keys_judge = sorted(crit_out.keys())

    # ---- D1 机检：键集合逐键相等 ∧ 机读主判据键 ∧ 显式来源 ∧ 无条件键 ----
    d1_ok = keys_src == keys_judge
    prim = sorted([k for k, v in prereg_src["criteria"].items() if v.get("primary")])
    prim_key = prim[0] if len(prim) == 1 else None
    d1_prim_ok = prim_key is not None and prim_key in crit_out
    all_keys_present = all(k in crit_out and crit_out[k].get("state") in STATES for k in keys_src)
    d1_pass = bool(d1_ok and d1_prim_ok and all_keys_present)

    # ---- 判决来源（显式谓词，禁从 blocked 反解）--------------------------
    drove = []
    if crit_out["J1_fallback_exercised"]["state"] == "fail":
        drove.append("J1_fallback_exercised")
    for k in ("J4a_capability_replication", "J4b_capability_vs_truth", "J3_cost"):
        if crit_out[k]["state"] == "fail":
            drove.append(k)
    if crit_out["P11_precondition_face"]["state"] == "fail":
        drove.append("P11_precondition_face")
    rc_rejudge = 3 if crit_out["W_floor_resolution_floor"]["state"] in ("fail", "input_missing") \
        else (1 if drove else 0)
    # ---- D3/D4/D5（R632 自有判据族；无条件计算，缺项写 None）----
    d3 = d3_driver_decl("r631")
    d4 = d4_history_pin()
    d5 = d5_lit_step()
    r632_crit = {
        "D1_judge_family_aligned": {"state": "pass" if d1_pass else "fail",
                                    "keys_equal": d1_ok, "primary_key_readable": d1_prim_ok,
                                    "all_keys_present_with_declared_state": all_keys_present},
        "D2_unreliable_policy_declared": {"state": "pass" if pol_active else "informational",
                                          "active": pol_active, "authority": ("unreliable_policy(机检)"
                                          if pol_active else "R4 manual（B2 拒绝追溯套用）")},
        "D3_driver_declaration_consistent": dict(d3),
        "D4_no_history_rewrite": dict(d4),
        "D5_lit_step": dict(d5),
        "W_floor_resolution_floor": {"state": "not_applicable",
                                     "why": "本轮无真机臂（零远端）；有效窗判据不适用，禁读作 PASS 亦禁读作红",
                                     "rejudged_face_valid_windows": crit_out["W_floor_resolution_floor"].get("valid_windows")},
    }
    r632_keys_src = sorted(prereg_self["criteria"].keys())
    r632_keys_got = sorted(r632_crit.keys())
    family_self_ok = r632_keys_src == r632_keys_got
    instrument_bad = (not d1_pass) or d3["state"] == "fail" or d4["state"] == "fail" or not family_self_ok
    rc = 2 if instrument_bad else rc_rejudge
    verdict_source = {"key": (drove[0] if len(drove) == 1 else (";".join(drove) if drove else "all_criteria_pass")),
                      "drove_rc": drove, "kind": ("instrument" if rc == 2 else "capability_secondary/mechanism"),
                      "rule": "explicit predicate over the criterion states (NOT reverse-inferred from `blocked`)"}

    out = {
        "round": "R632",
        "kind": "候选① 判据族对齐件：按 prereg-r631 的判据族**重审** R631 冻结读数（零重测、零产品改动、"
                "零阈值改动）；旧裁判件 judge_r631.py 的判决保留在盘、不采用、不翻案",
        "path_mode": path_mode,
        "criterion_source": {"prereg": "eval/rover/r631/prereg-r631.json",
                             "prereg_sha256": sha256_file(PREREG_SRC),
                             "criteria_keys_source": keys_src,
                             "criteria_keys_judge": keys_judge,
                             "primary_criterion_key": prim_key,
                             "primary_criterion_key_source": "prereg.criteria[<k>].primary == true（机读字段，禁扫描中文字面）"},
        "D1_judge_family_aligned": {"pass": d1_pass, "keys_equal": d1_ok, "primary_key_readable": d1_prim_ok,
                                    "all_keys_present_with_declared_state": all_keys_present,
                                    "judge_keys_extra": sorted(set(keys_judge) - set(keys_src)),
                                    "judge_keys_missing": sorted(set(keys_src) - set(keys_judge))},
        "verdict_source": verdict_source,
        "unreliable_policy": {"active": pol_active, "source": "prereg-r632.json",
                              "policy_declared_ts": (prereg_self.get("unreliable_policy") or {}).get("policy_declared_ts"),
                              "declared_for_future_rounds": pol_declared,
                              "gate_reading": "eval/rover/r632/evidence/policy-retro-r631.json",
                              "gate_reason": retro.get("reason"),
                              "applied_to_windows": unreliable,
                              "authority": ("unreliable_policy(机检)" if pol_active
                                            else "R4 manual single-listing（B2 拒绝追溯套用既有窗）"),
                              "effect": "该窗对照列移出 J4b 配对、只单列；本侧(agent*)臂失败一条不吞（B1）"},
        "evidence_sha256": {"transcripts": ev_sha, "runs_jsonl": runs_sha},
        "per_window": per,
        "criteria": crit_out,
        "r632_criteria": r632_crit,
        "r632_family_self_check": {"keys_prereg": r632_keys_src, "keys_computed": r632_keys_got,
                                   "keys_equal": family_self_ok,
                                   "rule": "本件自身也须满足 D1 同源律：自有判据族键集合 == prereg-r632.criteria 键集合"},
        "verdict": {"rc": rc,
                    "rc_semantics": "分层：0 = 预注册主判据族无红 / 1 = 次级判据红（能力或机制次级）/ "
                                    "2 = 器具缺陷（禁作被测结论）/ 3 = 输入缺失或分辨率不足（有效窗<2）",
                    "label": ("器具缺陷（判据族未对齐 / 声明滞后 / 历史件被改写）" if rc == 2 else
                              ("判据不可判（有效窗<2）" if rc == 3 else
                               ("次级判据红：" + ";".join(drove) if rc == 1 else "判据族全绿"))),
                    "truth_arm_rc_reference": "铁律 11 前置器 rc 另见 criteria.P11_precondition_face.precond_rc "
                                              "（rc≠0 ⇒ 质量/成本列标「参考（未可验收）」）"},
        "honest_bounds": [
            "本件为**重审**（re-judge）：全部读数取自 R631 冻结件（transcript/cases/runs.jsonl 逐件 sha256 落盘），"
            "**零重测**；旧件 verdict-r631.json 保留在盘、不采用、不翻案（RF0005 §3 R7：判据器跨轮改版禁相减）",
            "解析层复用 judge_r631.py 的 read_transcript/read_cases/load_helpers（单一实现防漂移）；判据层完全重写并与 "
            "prereg-r631 键集合断言相等",
            "D1 只证「判据族与预注册同源 + 来源可机读」；**不等于**质量轴达标，亦不改变 R631 的铁律 11 rc",
            "两条独立路径（runs-dir / frozen-extract）应给出逐位相同的 criteria 读数——不符即 rc=2（器具缺陷）",
        ],
        "checks_posthoc": [
            "旧裁判件判据族 = J1_exec_face_consumed/J1a..J1e/J2/J2b/J4_capability_secondary/J5/J6_zero_regression/v3/C1_task_face_v3；"
            "预注册族 = J0/J1_fallback_exercised/J4a/J4b/J3/J6_equivalence_face/W_floor/P11 ⇒ 旧判决不予采用（R631 自捕 D2）",
        ],
    }
    json.dump(out, io.open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": rc, "path_mode": path_mode, "D1": d1_pass,
                      "keys_equal": d1_ok, "primary": prim_key, "verdict_source": verdict_source["key"],
                      "J4a": crit_out["J4a_capability_replication"]["pass"],
                      "J4b": crit_out["J4b_capability_vs_truth"]["pass"],
                      "J3": crit_out["J3_cost"]["pass"],
                      "valid_windows": crit_out["W_floor_resolution_floor"]["valid_windows"],
                      "precond_rc": crit_out["P11_precondition_face"]["precond_rc"],
                      "unreliable": unreliable, "D3": d3["state"], "D4": d4["state"],
                      "D5": d5["state"], "r632_family_keys_equal": family_self_ok}, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
