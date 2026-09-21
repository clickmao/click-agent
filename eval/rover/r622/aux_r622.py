#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R622 三件辅助读数（只读，落盘 out/）：夹具普查 / 成本逐档分解 / CRASH stderr 取证。

全部**只读**：不改产品源码、不改 R621 冻结件、不调远端。
"""
from __future__ import annotations
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, os.path.join(REPO, "eval/rover/r622"))
import wythoff_oracle as ORC  # noqa: E402

PD = os.path.join(REPO, "eval/rover/r622")
OUT = os.path.join(PD, "out")
CASES = os.path.join(REPO, "eval/rover/r610/cases/cases-r521.json")
KPI = os.path.join(REPO, "eval/rover/r621/kpi-table-r621.json")
SNAP = os.path.join(REPO, "eval/rover/r621/snapshots")


def w(path, obj):
    io.open(os.path.join(OUT, path), "w", encoding="utf-8").write(
        json.dumps(obj, ensure_ascii=False, indent=1))


# ---------- ① 夹具普查：该族对「字典序最小」子型的判别力 ----------
def fixture_census():
    cases = [c for c in json.load(io.open(CASES, encoding="utf-8")) if c.get("game") == "wythoff"]
    rows = []
    for c in cases:
        a, b = (int(x) for x in c["stdin"].split()[:2])
        wins = ORC.winning_moves(a, b)
        rows.append({"in": "%d %d" % (a, b), "vis": c.get("vis"),
                     "losing": bool(ORC.LOSING[a][b]), "n_winning_moves": len(wins),
                     "expect": c["expected_stdout"].strip()})
    n = len(rows)
    n_lose = sum(1 for r in rows if r["losing"])
    n_single = sum(1 for r in rows if not r["losing"] and r["n_winning_moves"] == 1)
    return {
        "n_cases": n,
        "n_losing_cases": n_lose,
        "n_single_winning_move": n_single,
        "n_multi_winning_move": sum(1 for r in rows if not r["losing"] and r["n_winning_moves"] > 1),
        "rows": rows,
        "discriminating_power": {
            "M1_always_lose_correct": "%d/%d" % (n_lose, n),
            "M2_max_win_correct": "%d/%d" % (n_lose + n_single, n),
            "min_subtype_exercised": "%d/%d" % (n - n_lose - n_single, n),
            "note": "「取任意必胜着法」与「取字典序最小」仅在后者的多解例上分叉 ⇒ 该子型判别力 = n - n_losing - n_single。"
                    "M2 正确例 = 必败例(4) + 单解例(8) = 12，与变异负控实测 12/15 逐位吻合。",
        },
        "rule": "判别力 = 需要该子型才能正确的用例数 / 总用例数（退化解得分越低 ⇒ 判别力越强）",
    }


# ---------- ② 成本逐档分解（J3 差额的来源集中度）----------
def cost_decomp():
    k = json.load(io.open(KPI, encoding="utf-8"))
    rows = {r["臂"]: r for r in k["rows"]}
    T, C = rows["T"], rows["C"]
    d = [b - a for a, b in zip(T["新算prompt"], C["新算prompt"])]
    dc = [b - a for a, b in zip(T["调用"], C["调用"])]
    pos = [x for x in d if x > 0]
    abs_sum = sum(abs(x) for x in d)
    top = max(abs(x) for x in d)
    return {
        "sum_newprompt_T": sum(T["新算prompt"]), "sum_newprompt_C": sum(C["新算prompt"]),
        "sum_calls_T": sum(T["调用"]), "sum_calls_C": sum(C["调用"]),
        "sign_convention": "delta = 对照臂C - 治疗臂T（>0 ⇒ C 花得更多）",
        "net_newprompt_delta": sum(d), "abs_newprompt_delta_sum": abs_sum,
        "net_over_abs": round(abs(sum(d)) / abs_sum, 4),
        "top1_abs_delta": top,
        "top1_abs_delta_sign": "-" if d[[abs(x) for x in d].index(top)] < 0 else "+",
        "top1_share_of_abs_sum": round(top / abs_sum, 4),
        "concentration_ge_50pct": (top / abs_sum) >= 0.5,
        "per_slot_newprompt_delta": d,
        "per_slot_call_delta": dc,
        "net_call_delta": sum(dc),
        "call_delta_signs": {"neg": sum(1 for x in dc if x < 0), "pos": sum(1 for x in dc if x > 0)},
        "rule": "集中度 = 单档最大 |Δ| / Σ|Δ|；另看 净差/Σ|Δ|。两者都 < 0.5 ⇒ 差额是摆动残差 ⇒ 不可归因到轴",
        "verdict": "NO_CONCENTRATED_SOURCE" if (top / abs_sum) < 0.5 else "CONCENTRATED",
    }


# ---------- ③ CRASH stderr 取证（一轮，取首个崩溃产物）----------
def crash_probe():
    pc = json.load(io.open(os.path.join(OUT, "percase-r622.json"), encoding="utf-8"))
    bad = [r for r in pc["rows"] if r["tag"] == "HARD_CRASH"]
    if not bad:
        return {"n_crash_rows": 0, "note": "无崩溃例"}
    r0 = bad[0]
    base = os.path.join(SNAP, r0["win"], r0["arm_id"])
    trees = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
    src = os.path.join(base, trees[0], "games/wythoff.py") if trees else ""
    res = {"n_crash_rows": len(bad),
           "crash_by_arm": {a: sum(1 for r in bad if r["arm"] == a)
                            for a in sorted({r["arm"] for r in bad})},
           "probe_row": {k: r0[k] for k in ("win", "arm", "arm_id", "rep", "case", "a", "b", "rc")},
           "source": src}
    if not (trees and os.path.isfile(src)):
        res["note"] = "源件不存在"
        return res
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    tmp = tempfile.mkdtemp(prefix="r622crash-")
    try:
        dst = os.path.join(tmp, "t")
        shutil.copytree(os.path.dirname(os.path.dirname(src)), dst)
        f = os.path.join(dst, "games/wythoff.py")
        env2 = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": dst,
                "PYTHONPATH": dst, "PYTHONDONTWRITEBYTECODE": "1"}
        p = subprocess.run([sys.executable, "-B", "-m", "games", "wythoff"],
                           input="%d %d\n" % (r0["a"], r0["b"]),
                           capture_output=True, text=True, timeout=30, cwd=dst, env=env2)
        res["invocation"] = "python3 -B -m games wythoff (cwd=tree, PYTHONPATH=tree)"
        res["rc"] = p.returncode
        res["stdout"] = p.stdout.strip()[:200]
        res["stderr_tail"] = "\n".join(p.stderr.strip().splitlines()[-6:])
        m = None
        for cand in re.finditer(r'File "([^"]+)", line (\d+)', p.stderr):
            if os.path.basename(cand.group(1)) == "wythoff.py":
                m = cand
        if m is None:
            m = list(re.finditer(r'File "([^"]+)", line (\d+)', p.stderr))
            m = m[-1] if m else None
        res["error_site"] = {"file": os.path.basename(m.group(1)) if m else None,
                             "line": int(m.group(2)) if m else None}
        if m:
            lines = io.open(f, encoding="utf-8").read().splitlines()
            ln = int(m.group(2))
            res["error_source_line"] = lines[ln - 1].strip() if 0 < ln <= len(lines) else None
        res["reproduced"] = (p.returncode != 0 and not p.stdout.strip())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    w("fixture-census-r622.json", fixture_census())
    w("cost-decomp-r622.json", cost_decomp())
    w("crash-stderr-r622.json", crash_probe())
    print("census:", json.dumps(fixture_census()["discriminating_power"], ensure_ascii=False))
    print("cost  :", json.dumps({k: v for k, v in cost_decomp().items()
                                 if k not in ("per_slot_newprompt_delta", "per_slot_call_delta")},
                                ensure_ascii=False))
    c = crash_probe()
    print("crash : rc=%s site=%s line=%s" % (c.get("rc"), (c.get("error_site") or {}).get("file"),
                                             (c.get("error_site") or {}).get("line")))
    print("        src_line=%s" % c.get("error_source_line"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
