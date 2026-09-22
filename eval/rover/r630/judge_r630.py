#!/usr/bin/env python3
"""R630 判据器（单变量轴 = `AGENTFRAMEWORK_R1_ACTION_PROMPT` 第四取值 `spec`）。

读取契约（**先钉死再判**，R-EXP1-Q39 ④）:
  · 前缀锚**不写常量** ⇒ 从 `eval/rover/r630/prefix-r630.json`（冻结读数）取 default/spec 两档 chars+sha256；
    该件缺失或 checks 不全绿 ⇒ rc=2 器具缺陷（禁计入被测读数）。
  · 逐跑次输入 = `<D>/<win>/<sub>/g1/transcript.json`（落盘形态 = **单对象 JSON**，非 JSONL），
    字段路径全在**顶层**：prefix_chars / prefix_sha256 / calls / prompt_tokens / completion_tokens /
    cache_hit_tokens / cache_miss_tokens。
  · 逐跑次质量 = `<D>/<win>/<sub>/g1/cases.txt`（`run_cases_r521.py` 输出；取 "PASS/TOTAL" 形态）。
  · 字段缺失一律 fail-closed 为**器具缺陷/输入缺失**（rc=2/3），禁算作被测不达标。

J 面: J0 臂轴生效（fail-closed）· J1 机制面 · J2 质量面（T 不劣于 C）· J3 成本面 · J4 零回归（C 档 == 缺省 pin）。
rc: 0 = 机制 PASS ∧ 能力不劣 / 1 = 被测不满足 / 2 = 器具缺陷或 VOID / 3 = 输入缺失或有效窗 < 2。

自检（影子自检，四态夹具回放）: python3 judge_r630.py --selftest
用法: python3 eval/rover/r630/judge_r630.py --D <dir> --pd <repo/eval/rover/r630>
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
import tempfile

CASES_RE = re.compile(r"(\d+)\s*/\s*(\d+)")
CASES_PIN_RE = re.compile(r"R521_CASES\s+(\d+)\s*/\s*(\d+)")


def die(msg, rc=2):
    print("JUDGE_DEFECT: %s" % msg)
    return rc


def load_anchors(pd):
    p = os.path.join(pd, "prefix-r630.json")
    if not os.path.isfile(p):
        return None, "缺冻结前缀读数 %s" % p
    d = json.load(io.open(p, encoding="utf-8"))
    if not all(d.get("checks", {}).values()):
        return None, "冻结前缀读数 checks 未全绿"
    return {
        "default": (d["pin_current"]["chars"], d["pin_current"]["sha256"]),
        "spec": (d["pin_spec_tier"]["chars"], d["pin_spec_tier"]["sha256"]),
    }, None


def read_transcript(path):
    if not os.path.isfile(path):
        return None, "missing"
    try:
        return json.load(io.open(path, encoding="utf-8")), None
    except Exception as e:  # noqa: BLE001
        return None, "unparsable:%s" % e


def read_cases(path):
    if not os.path.isfile(path):
        return None, "missing"
    txt = io.open(path, encoding="utf-8", errors="replace").read()
    # 契约优先：只认判分器自报的聚合行 `R521_CASES p/t`（泛比率为兜底）
    m = CASES_PIN_RE.search(txt)
    if m:
        return (int(m.group(1)), int(m.group(2))), None
    best = None
    for m in CASES_RE.finditer(txt):
        a, b = int(m.group(1)), int(m.group(2))
        if b > 0:
            best = (a, b)
    if best is None:
        return None, "no_ratio"
    return best, "fallback_regex"


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def collect(D, anchors, wins, subs):
    """返回 {(win, sub): rec}，rec 内含前缀/成本/质量读数与缺陷清单。"""
    recs = {}
    missing = []
    for W in wins:
        for sub in subs:
            base = os.path.join(D, W, sub, "g1")
            if not os.path.isdir(base):
                missing.append("%s/%s" % (W, sub))
                continue
            tr, err = read_transcript(os.path.join(base, "transcript.json"))
            cs, cerr = read_cases(os.path.join(base, "cases.txt"))
            fmt = "spec" if sub.startswith("agentT") else "default"
            rec = {"win": W, "sub": sub, "fmt_expected": fmt,
                   "prefix_chars": (tr or {}).get("prefix_chars"),
                   "prefix_sha256": (tr or {}).get("prefix_sha256"),
                   "rc": (tr or {}).get("rc"),
                   "stage": (tr or {}).get("stage"),
                   "steps_executed": (tr or {}).get("steps_executed"),
                   "plan_steps_total": (tr or {}).get("plan_steps_total"),
                   "reason": (tr or {}).get("reason"),
                   "calls": (tr or {}).get("calls"),
                   "prompt_tokens": (tr or {}).get("prompt_tokens"),
                   "completion_tokens": (tr or {}).get("completion_tokens"),
                   "cache_hit_tokens": (tr or {}).get("cache_hit_tokens"),
                   "cache_miss_tokens": (tr or {}).get("cache_miss_tokens"),
                   "cases": cs, "tr_err": err, "cases_err": cerr}
            arm = "T" if sub.startswith("agentT") else "C"
            exp = anchors["spec"] if arm == "T" else anchors["default"]
            rec["fmt_match"] = (rec["prefix_chars"] == exp[0] and rec["prefix_sha256"] == exp[1])
            recs[(W, sub)] = rec
    return recs, missing


def verdict(D, pd, wins, subs):
    anchors, aerr = load_anchors(pd)
    if aerr:
        return {"rc": 2, "defects": [aerr], "label": "VOID(器具缺陷: 前缀锚不可读)"}
    assert anchors is not None
    A_DEF, A_SPEC = anchors["default"], anchors["spec"]
    recs, missing = collect(D, anchors, wins, subs)
    defects, notes = [], []

    unreadable = [k for k, r in recs.items() if r["tr_err"] or r["cases_err"]]
    if unreadable:
        return {"rc": 3, "defects": ["输入缺失/不可读: %s" % unreadable[:6]],
                "label": "弃权(输入缺失)", "recs": list(recs.values()),
                "anchors": anchors, "missing": missing}

    # ---- VOID 闸（fail-closed）：**未达模型**的跑次不得进能力/成本面 -------------------
    # 判据 = `calls >= 1` ∧ `stage != llm_transport`（= 上游调用真发生）。
    # **rc != 0 不是 VOID**：rc=5/8 是「计划未跑完 / 自测未达成」的**能力面**读数（有模型调用、
    #   有落盘产物），把它当 VOID 会把能力信号静默丢弃（本轮 v2 判据器实测误判 5/12 跑次 ⇒ 停链）。
    # 字段缺失 ⇒ 契约不符（rc=3），禁算作被测不达标。
    allruns = list(recs.values())
    field_missing = [r["sub"] for r in allruns if r["rc"] is None or r["calls"] is None or r["stage"] is None]
    if field_missing:
        return {"rc": 3, "defects": ["transcript 缺 rc/calls/stage 字段（读取契约不符）: %s" % field_missing[:6]],
                "label": "弃权(读取契约不符)", "recs": allruns, "anchors": anchors}
    void_runs = [r for r in allruns if (r["calls"] or 0) < 1 or r["stage"] == "llm_transport"]
    if len(void_runs) == len(allruns):
        return {"rc": 2, "defects": ["全部跑次 VOID（未达模型: calls=0 或 stage=llm_transport）: %s" %
                                     sorted({(r["calls"], r["stage"]) for r in void_runs})],
                "label": "VOID(无有效跑次 ⇒ 能力/成本面不可判，禁 PASS)",
                "void_runs": [r["sub"] for r in void_runs], "recs": allruns, "anchors": anchors,
                "notes": ["首个 VOID 原因: %s" % (void_runs[0].get("reason") or "")[:160]]}
    valid = [r for r in allruns if r not in void_runs]
    recs = {(r["win"], r["sub"]): r for r in valid}
    # 计划未跑完（能力面读数，**不是** VOID）：rc != 0 且已真实调用
    plan_incomplete = {r["sub"]: {"rc": r["rc"], "stage": r["stage"],
                                  "steps": "%s" % r.get("steps_executed")} for r in valid if r["rc"] != 0}

    T = [r for r in recs.values() if r["fmt_expected"] == "spec"]
    C = [r for r in recs.values() if r["fmt_expected"] == "default"]

    # J0 臂轴生效（fail-closed 器具闸）：逐跑次前缀读数 == 该臂锚 ∧ 两档读数集合不相交
    bad_T = [r["sub"] for r in T if not r["fmt_match"]]
    bad_C = [r["sub"] for r in C if not r["fmt_match"]]
    tset = {(r["prefix_chars"], r["prefix_sha256"]) for r in T}
    cset = {(r["prefix_chars"], r["prefix_sha256"]) for r in C}
    distinguishable = bool(tset) and bool(cset) and not (tset & cset)
    j0 = (not bad_T) and (not bad_C) and distinguishable
    if bad_T:
        defects.append("J0 T 档前缀读数不等于 spec 锚: %s" % bad_T[:6])
    if bad_C:
        defects.append("J0 C 档前缀读数不等于缺省锚（零回归破）: %s" % bad_C[:6])
    if not distinguishable:
        defects.append("J0 两档读数不可区分（T∩C 非空或空集）")

    # J1 机制面：T 档**出现 spec 档读数**的跑次数 >= 1 ∧ C 档出现 spec 档读数的次数 == 0
    #   （判据是「谁读到了 spec 档」，不是「谁匹配了自己那档锚」——后者对 C 恒真 ⇒ 空心判据，本轮实测踩到）
    spec_cnt = lambda rs: sum(1 for r in rs if (r["prefix_chars"], r["prefix_sha256"]) == anchors["spec"])
    j1 = spec_cnt(T) >= 1 and spec_cnt(C) == 0

    # J2 质量面（逐窗中位差 >= 0 ∧ 整题全对率不下降）
    per_win, j2 = {}, True
    for W in wins:
        tw = [r for r in T if r["win"] == W and r["cases"]]
        cw = [r for r in C if r["win"] == W and r["cases"]]
        if not tw or not cw:
            per_win[W] = {"note": "窗内臂样本缺（有效窗剔除）"}
            continue
        tm = median([r["cases"][0] for r in tw])
        cm = median([r["cases"][0] for r in cw])
        ta = median([1.0 if r["cases"][0] == r["cases"][1] else 0.0 for r in tw])
        ca = median([1.0 if r["cases"][0] == r["cases"][1] else 0.0 for r in cw])
        per_win[W] = {"T_median_pass": tm, "C_median_pass": cm, "T_allpass": ta, "C_allpass": ca,
                      "total": tw[0]["cases"][1],
                      "T_min_pass": min(r["cases"][0] for r in tw), "C_min_pass": min(r["cases"][0] for r in cw),
                      "T_fails": sum(r["cases"][1] - r["cases"][0] for r in tw),
                      "C_fails": sum(r["cases"][1] - r["cases"][0] for r in cw),
                      "T_spread": [min(r["cases"][0] for r in tw), max(r["cases"][0] for r in tw)],
                      "C_spread": [min(r["cases"][0] for r in cw), max(r["cases"][0] for r in cw)]}
        if tm is None or cm is None or tm < cm or ta < ca:
            j2 = False

    # §3 摆动 vs 效应（判该轴是不是承重变量）：摆动 = 同臂跨窗/跨重复摆幅的最大值；效应 = 逐窗中位差的绝对值
    swing = 0
    effect = 0
    for W, m in per_win.items():
        if m.get("T_median_pass") is None:
            continue
        swing = max(swing, (m["T_spread"][1] - m["T_spread"][0]) if m.get("T_spread") else 0,
                    (m["C_spread"][1] - m["C_spread"][0]) if m.get("C_spread") else 0)
        effect = max(effect, abs(m["T_median_pass"] - m["C_median_pass"]))
    axis_verdict = ("定案关闭（摆动 %d >= 效应 %d ⇒ 该轴非承重变量，禁调阈值）" % (swing, effect)
                    if swing >= effect else "未定（效应 %d > 摆动 %d ⇒ 需扩窗/reps 复核）" % (effect, swing))

    valid_wins = [W for W in wins if per_win.get(W, {}).get("T_median_pass") is not None]
    if len(valid_wins) < 2:
        notes.append("有效窗 = %d (<2) ⇒ 按 §3 停链先造窗, 禁作能力结论" % len(valid_wins))

    # J3 成本面（三列分列，禁名义总量）
    def agg(rs):
        return {"runs": len(rs),
                "calls": sum(r["calls"] or 0 for r in rs),
                "prompt_tokens": sum(r["prompt_tokens"] or 0 for r in rs),
                "completion_tokens": sum(r["completion_tokens"] or 0 for r in rs),
                "cache_hit_tokens": sum(r["cache_hit_tokens"] or 0 for r in rs),
                "cache_miss_tokens": sum(r["cache_miss_tokens"] or 0 for r in rs)}
    cost = {"T": agg(T), "C": agg(C)}
    tc = median([r["completion_tokens"] or 0 for r in T])
    cc = median([r["completion_tokens"] or 0 for r in C])
    inflation = None
    if tc is not None and cc:
        inflation = round(tc / float(cc), 3)
    j3 = not (inflation is not None and inflation > 1.5)

    # J4 零回归（C 档逐位等于缺省 pin）
    j4 = all(r["fmt_match"] for r in C) and sum(1 for r in C if r["prefix_sha256"] == anchors["default"][1]) == len(C)

    if not j0:
        rc, label = 2, "VOID(臂轴未生效 ⇒ 禁作被测结论)"
    elif not j1:
        rc, label = 2, "VOID(机制面未生效: T 档无 spec 读数或 C 档出现 spec 读数 ⇒ 器具/接线缺陷)"
    elif len(valid_wins) < 2:
        rc, label = 3, "停链(有效窗<2, 禁下调阈值)"
    elif j2:
        rc, label = (0, "机制 PASS ∧ 能力面不劣于对照（中位持平；见 swing_vs_effect 的轴裁定）"
                     if swing >= effect else
                     "机制 PASS ∧ 能力面优于对照（效应用 > 摆动）")
    else:
        rc, label = 1, "被测不满足(质量面劣于对照)"
    if not j3:
        notes.append("J3 completion 膨胀 >1.5x（成本面告警，不改判）")
    if not j4:
        defects.append("J4 C 档未逐位等于缺省 pin")

    return {"rc": rc, "label": label, "J0": j0, "J1": j1, "J2": j2, "J3": j3, "J4": j4,
            "per_window": per_win, "cost": cost, "completion_inflation_T_over_C": inflation,
            "anchors": anchors, "defects": defects, "notes": notes,
            "swing_vs_effect": {"swing": swing, "effect": effect}, "axis_verdict": axis_verdict,
            "plan_incomplete": plan_incomplete, "void_runs": [r["sub"] for r in void_runs],
            "missing_runs": missing, "recs": list(recs.values())}


# ---------------------------------------------------------------- 影子自检
def _mk(D, W, sub, chars, sha, cases, calls=3, pt=9000, ct=400, ch=8000, cm=1000, rc=0, stage="ok"):
    base = os.path.join(D, W, sub, "g1")
    os.makedirs(base, exist_ok=True)
    json.dump({"stage": stage, "rc": rc, "prefix_chars": chars, "prefix_sha256": sha, "calls": calls,
               "prompt_tokens": pt, "completion_tokens": ct, "cache_hit_tokens": ch,
               "cache_miss_tokens": cm, "steps_executed": 3},
              io.open(os.path.join(base, "transcript.json"), "w", encoding="utf-8"), ensure_ascii=False)
    io.open(os.path.join(base, "cases.txt"), "w", encoding="utf-8").write(
        "CASE c1 PASS ok@0.10s\nR521_CASES %d/%d\n" % (cases, cases))


def selftest(pd):
    anchors, err = load_anchors(pd)
    if err:
        print("SELFTEST_FAIL(锚不可读): %s" % err)
        return 2
    dc, ds = anchors["default"], anchors["spec"]
    cases = []

    # S1 正常：T=spec / C=default / 质量持平 ⇒ rc=0
    D = tempfile.mkdtemp(prefix="j630-s1-")
    for r in (1, 2):
        _mk(D, "w211", "agentT-r%d" % r, ds[0], ds[1], 60)
        _mk(D, "w212", "agentT-r%d" % r, ds[0], ds[1], 58)
        _mk(D, "w211", "agentC-r%d" % r, dc[0], dc[1], 60)
        _mk(D, "w212", "agentC-r%d" % r, dc[0], dc[1], 58)
    cases.append(("S1_normal", verdict(D, pd, ["w211", "w212"], ["agentT-r1", "agentT-r2", "agentC-r1", "agentC-r2"])["rc"], 0))

    # S2 变异（负控）：T 档前缀仍是缺省 ⇒ 轴未生效 ⇒ 必 VOID rc=2
    D2 = tempfile.mkdtemp(prefix="j630-s2-")
    for r in (1, 2):
        _mk(D2, "w211", "agentT-r%d" % r, dc[0], dc[1], 60)
        _mk(D2, "w211", "agentC-r%d" % r, dc[0], dc[1], 60)
    cases.append(("S2_mutation_axis_dead", verdict(D2, pd, ["w211"], ["agentT-r1", "agentT-r2", "agentC-r1", "agentC-r2"])["rc"], 2))

    # S3 质量劣：T 中位 < C 中位 ⇒ rc=1
    D3 = tempfile.mkdtemp(prefix="j630-s3-")
    for r in (1, 2):
        _mk(D3, "w211", "agentT-r%d" % r, ds[0], ds[1], 50)
        _mk(D3, "w212", "agentT-r%d" % r, ds[0], ds[1], 50)
        _mk(D3, "w211", "agentC-r%d" % r, dc[0], dc[1], 60)
        _mk(D3, "w212", "agentC-r%d" % r, dc[0], dc[1], 60)
    cases.append(("S3_quality_worse", verdict(D3, pd, ["w211", "w212"], ["agentT-r1", "agentT-r2", "agentC-r1", "agentC-r2"])["rc"], 1))

    # S4 字段缺失 ⇒ 弃权 rc=3（**不是**红）
    D4 = tempfile.mkdtemp(prefix="j630-s4-")
    _mk(D4, "w211", "agentT-r1", ds[0], ds[1], 60)
    os.remove(os.path.join(D4, "w211", "agentT-r1", "g1", "transcript.json"))
    cases.append(("S4_missing_field", verdict(D4, pd, ["w211"], ["agentT-r1"])["rc"], 3))

    # S5 单窗（有效窗 <2）⇒ rc=3 停链
    D5 = tempfile.mkdtemp(prefix="j630-s5-")
    for r in (1, 2):
        _mk(D5, "w211", "agentT-r%d" % r, ds[0], ds[1], 60)
        _mk(D5, "w211", "agentC-r%d" % r, dc[0], dc[1], 60)
    cases.append(("S5_single_window", verdict(D5, pd, ["w211"], ["agentT-r1", "agentT-r2", "agentC-r1", "agentC-r2"])["rc"], 3))

    # S6 全跑次 VOID（rc=6/llm_transport, calls=0）⇒ 必判 rc=2（**不得**因前缀读数正常而 PASS）
    D6 = tempfile.mkdtemp(prefix="j630-s6-")
    for r in (1, 2):
        _mk(D6, "w211", "agentT-r%d" % r, ds[0], ds[1], 0, calls=0, rc=6, stage="llm_transport")
        _mk(D6, "w211", "agentC-r%d" % r, dc[0], dc[1], 0, calls=0, rc=6, stage="llm_transport")
    cases.append(("S6_all_void", verdict(D6, pd, ["w211"], ["agentT-r1", "agentT-r2", "agentC-r1", "agentC-r2"])["rc"], 2))

    # S7 计划未跑完（rc=5, calls>=1）：**不得**判 VOID ⇒ 进能力面（质量持平 ⇒ rc=0）
    D7 = tempfile.mkdtemp(prefix="j630-s7-")
    for r in (1, 2):
        _mk(D7, "w211", "agentT-r%d" % r, ds[0], ds[1], 58, calls=2, rc=5, stage="expect_stdout_exhausted")
        _mk(D7, "w211", "agentC-r%d" % r, dc[0], dc[1], 58, calls=2, rc=5, stage="expect_stdout_exhausted")
        _mk(D7, "w212", "agentT-r%d" % r, ds[0], ds[1], 58, calls=2, rc=0, stage="done")
        _mk(D7, "w212", "agentC-r%d" % r, dc[0], dc[1], 58, calls=2, rc=0, stage="done")
    cases.append(("S7_plan_incomplete_not_void",
                  verdict(D7, pd, ["w211", "w212"], ["agentT-r1", "agentT-r2", "agentC-r1", "agentC-r2"])["rc"], 0))

    for d in (D, D2, D3, D4, D5, D6, D7):
        shutil.rmtree(d, ignore_errors=True)
    ok = all(got == want for _, got, want in cases)
    for name, got, want in cases:
        print("  %-24s got=%s want=%s %s" % (name, got, want, "OK" if got == want else "MISMATCH"))
    print("SELFTEST_%s rc=%d" % ("PASS" if ok else "FAIL", 0 if ok else 2))
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D")
    ap.add_argument("--pd", default=os.path.join(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--win", action="append", default=None)
    ap.add_argument("--subs", default="agentT-r1,agentT-r2,agentT-r3,agentC-r1,agentC-r2,agentC-r3")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.selftest:
        return selftest(a.pd)
    if not a.D:
        return die("缺 --D")
    wins = a.win or ["w211", "w212"]
    subs = [s for s in a.subs.split(",") if s]
    v = verdict(a.D, a.pd, wins, subs)
    if a.out:
        json.dump(v, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v[k] for k in ("rc", "label", "J0", "J1", "J2", "J3", "J4",
                                        "completion_inflation_T_over_C", "defects", "notes")},
                     ensure_ascii=False))
    return v["rc"]


if __name__ == "__main__":
    sys.exit(main())
