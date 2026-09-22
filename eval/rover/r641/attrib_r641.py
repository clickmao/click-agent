#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R641 · 只读逐例归因（承 R640 下轮候选 ①②③）—— 逐行级定因 + 帧感知分类 + 分辨率条款。

改哪一格读数：**不改动任何既有读数**（零产品改动 / 零重测 / 零新臂）。把 R640 遗留的
「J4 未定因 4/5」从「候选补丁全不生效」推进为「读源码后定位到具体行」的最小修复实验，
并暴露 R640 判据器的一处**帧不感知**误标（`nonwinning_move`）。

设计约束（承 R637/R640 + unattended-job-reliability 教训）：
  · 最小修复锚点**逐字取自现盘源码**，每处断言 `替换次数 == 1`；锚点缺失 ⇒ `ANCHOR_MISS` +
    fail-closed（记「未测到」，禁读作「无缺陷」）；
  · 必配**空重写负控**（同字节重写同一文件 ⇒ 目标族仍全败且与 base 逐位相同）；
  · 分类器**帧感知**：(i,j) 在其转置 (j,i) 为必胜着法时判 `FRAME_TRANSPOSE`（表示面缺陷）；
  · **分块增量落盘 + 断点续跑缓存**（一次晚段崩溃不得丢掉已得的昂贵读数）；
  · 探针/mutant **自身不得抛异常**（缺陷信息构造自身崩 ⇒ 会把真因掩盖成另一种错误）；
  · 只读：一切执行在**副本**上进行，零写入冻结树。

用法：
  python3 attrib_r641.py                # 全量归因 → out/attrib-r641.json
"""
from __future__ import annotations
import argparse
import hashlib
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

SNAP = os.path.join(REPO, "eval/rover/r639/snapshots")
CASES = os.path.join(REPO, "eval/rover/r639/cases/cases-r521.json")
R639_VERDICT = os.path.join(REPO, "eval/rover/r639/verdict-r639.json")
R640_ATTRIB = os.path.join(REPO, "eval/rover/r640/out/attrib-r640.json")
OUTDIR = os.path.join(REPO, "eval/rover/r641/out")
OUT = os.path.join(OUTDIR, "attrib-r641.json")
CACHE_REPLAY = os.path.join(OUTDIR, ".cache-replay-r641.json")
CACHE_J4 = os.path.join(OUTDIR, ".cache-j4-r641.json")
FAMS = ["life", "sub", "nim", "wythoff"]
WINS = ["w237", "w238", "w239"]
SUBS = ["agentP-r1", "agentP-r2", "agentP-r3", "codex"]
TMO = 60.0


def sha256(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def save(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False, indent=1))


def jload(path):
    return json.load(io.open(path, encoding="utf-8")) if os.path.exists(path) else None


def load_cases():
    return json.load(io.open(CASES, encoding="utf-8"))


def run_probe(tree, fam, stdin, tmo=TMO):
    """在**副本**上跑 `python3 -B -m games <fam>`（零写入冻结树）。"""
    tmp = tempfile.mkdtemp(prefix="r641p-")
    dst = os.path.join(tmp, "t")
    try:
        shutil.copytree(tree, dst)
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": dst,
               "PYTHONPATH": dst, "PYTHONDONTWRITEBYTECODE": "1"}
        p = subprocess.run([sys.executable, "-B", "-m", "games", fam], input=stdin,
                           capture_output=True, text=True, timeout=tmo, cwd=dst, env=env)
        return p.returncode, (p.stdout or ""), (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "", "TimeoutExpired"
    except Exception as e:  # noqa: BLE001
        return 125, "", type(e).__name__
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def fam_scores(tree, cases):
    res = {}
    for fam in FAMS:
        ok = 0
        for c in cases:
            if c["game"] != fam:
                continue
            rc, out, _ = run_probe(tree, fam, c["stdin"])
            if rc == 0 and out.strip("\n") == c["expected_stdout"].strip("\n"):
                ok += 1
        res[fam] = ok
    return res


WIN_RE = re.compile(r"^WIN (\d+) (\d+)$")


def classify_case(rc, out, c):
    """帧感知单例分类 → (标签, 细节)。"""
    a, b = (int(x) for x in c["stdin"].split()[:2])
    exp, got = c["expected_stdout"].strip("\n"), out.strip("\n")
    if rc != 0 or got == "":
        return "HARD_CRASH", "rc=%d len=%d" % (rc, len(got))
    if got == exp:
        return "OK", ""
    if got == "LOSE" or exp == "LOSE":
        return "STATE_FLIP", "exp=%r got=%r" % (exp[:24], got[:24])
    m = WIN_RE.match(got)
    if not m:
        return "FORMAT", "got=%r" % got[:40]
    i, j = int(m.group(1)), int(m.group(2))
    legal = (0 <= i <= a) and (0 <= j <= b) and (i, j) != (0, 0) and (i == 0 or j == 0 or i == j)
    inb = 0 <= i <= a and 0 <= j <= b
    reaches = ORC.LOSING[a - i][b - j] if inb else False
    if legal and reaches:
        return "LEGAL_NONMIN", "legal_winning_but_not_min=(%d,%d)" % (i, j)
    t_legal = (0 <= j <= a) and (0 <= i <= b) and (i, j) != (0, 0) and (j == 0 or i == 0 or i == j)
    t_reaches = ORC.LOSING[a - j][b - i] if (0 <= j <= a and 0 <= i <= b) else False
    if t_legal and t_reaches:
        return "FRAME_TRANSPOSE", "transposed_move=(%d,%d)_is_winning" % (j, i)
    if not legal:
        return "ILLEGAL_MOVE", "illegal_move=(%d,%d)" % (i, j)
    return "TRUE_WRONG", "nonwinning_move=(%d,%d)" % (i, j)


def oracle_control(cases):
    wy = [c for c in cases if c["game"] == "wythoff"]
    pos = sum(1 for c in wy if ORC.solve(c["stdin"]).strip() == c["expected_stdout"].strip())
    saved = ORC.LOSING[6][10], ORC.LOSING[10][6]
    ORC.LOSING[6][10] = ORC.LOSING[10][6] = not ORC.LOSING[6][10]
    try:
        mut = sum(1 for c in wy if ORC.solve(c["stdin"]).strip() == c["expected_stdout"].strip())
    finally:
        ORC.LOSING[6][10], ORC.LOSING[10][6] = saved
    return {"positive": "%d/%d" % (pos, len(wy)), "positive_pass": pos == len(wy),
            "mutant_pass": "%d/%d" % (mut, len(wy)), "mutant_teeth": mut < pos,
            "pass": pos == len(wy) and mut < pos}


def expectations():
    """期望表机取（两条独立来源；缺源 ⇒ rc=3，两源不符 ⇒ rc=2 器具层 fail-closed）。"""
    for p in (R639_VERDICT, R640_ATTRIB):
        if not os.path.exists(p):
            return None, {"rc": 3, "why": "missing_source:%s" % p}
    v639 = json.load(io.open(R639_VERDICT, encoding="utf-8"))
    a640 = json.load(io.open(R640_ATTRIB, encoding="utf-8"))
    by_run = {("%s/%s" % (r["win"], r["sub"])): r for r in v639["B_family_block"]["by_run"]}
    per640 = a640["per_run_wythoff"]
    table, mismatch = {}, []
    for win in WINS:
        for sub in SUBS:
            run = "%s/%s" % (win, sub)
            if run in by_run:
                wy = by_run[run]["families"]["wythoff"]
                pass_run = by_run[run]["cases"] == "58/58"
                src = "r639.verdict.B_family_block.by_run"
                if run in per640 and int(wy.split("/")[0]) != per640[run]["pass"]:
                    mismatch.append({"run": run, "r639": int(wy.split("/")[0]),
                                     "r640": per640[run]["pass"]})
            elif run in per640:
                pass_run = per640[run]["pass"] == 15
                src = "r640.attrib.per_run_wythoff(第二源)"
            else:
                return None, {"rc": 3, "why": "no_expectation_for:%s" % run}
            table[run] = {"pass_run": bool(pass_run), "wythoff_source": src}
    if mismatch:
        return None, {"rc": 2, "why": "expectation_sources_disagree", "detail": mismatch}
    return table, {"rc": 0, "sources": ["r639.verdict", "r640.attrib"], "n": len(table)}


MINFIX = {
    "w237/agentP-r3": [
        {"id": "L7_idx_is_pair_index_not_ratio",
         "why": "必败位索引应为配对序号 b-a，写成 (b-a)/φ ⇒ 窗口 idx-1..idx+2 在大 n 上取不到真 n",
         "ops": [("    idx = int((b - a) / PHI) if b > a else 0",
                  "    idx = (b - a) if b > a else 0")]},
    ],
    "w238/agentP-r3": [
        {"id": "L36_frame_swap_left_undone",
         "why": "solve 内部把两堆排序后**未换回输入帧** ⇒ 着法按排序帧表示（规格要求第一堆 = 读入的 a）",
         "ops": [("\n    if a > b:\n        a, b = b, a\n", "\n")]},
    ],
    "w239/agentP-r1": [
        {"id": "L40_search_range_starts_at_n",
         "why": "二分区间起点写成 n（谓词在 mid=n 处立即为假 ⇒ 循环零次，函数恒返回 n）",
         "ops": [("    lo, hi = n, 2 * n + 1", "    lo, hi = 0, n")]},
        {"id": "L47_missing_plus_n",
         "why": "⌊nφ⌋ = n + ⌊n/φ⌋；返回只给 ⌊n/φ⌋ ⇒ 缺 +n 分量",
         "ops": [("\n    return lo\n", "\n    return lo + n\n")]},
    ],
    "w239/agentP-r2": [
        {"id": "L6_00_not_seeded_losing",
         "why": "(0,0) 被 `continue` 跳过而**未入必败集**（DP 初值缺）⇒ 整张必败集错位",
         "ops": [("            if i == 0 and j == 0:\n                continue\n            win = ",
                  "            if i == 0 and j == 0:\n                los.add((i, j))\n                continue\n            win = ")]},
        {"id": "L32_selection_tests_candidate_not_result",
         "why": "着法选择判的是候选 (i,j) 自身是否在必败集，而非**走完后的落点** (a-i,b-j)",
         "ops": [("            if (i, j) not in los:\n                continue\n",
                  "            if (a - i, b - j) not in los:\n                continue\n")]},
    ],
    "w239/codex": [
        {"id": "L22_move_loop_missing_legality_filter",
         "why": "着法枚举未限定合法着法 ⇒ 非法着法被当候选（真值臂自身缺陷）",
         "ops": [("            if i == 0 and j == 0:\n                continue\n            if (a - i, b - j) in losing_set:",
                  "            if i == 0 and j == 0:\n                continue\n            if not (i == 0 or j == 0 or i == j):\n                continue\n            if (a - i, b - j) in losing_set:")]},
    ],
}


def minfix_run(run, cases):
    src = os.path.join(SNAP, run, "g1", "games", "wythoff.py")
    raw = io.open(src, encoding="utf-8").read()
    base = fam_scores(os.path.join(SNAP, run, "g1"), cases)
    out = {"run": run, "src_sha256": sha256(src), "baseline_families": base, "attempts": []}
    for cand in MINFIX.get(run, []):
        patched, ok = raw, True
        for old, new in cand["ops"]:
            patched, n = re.subn(re.escape(old), lambda m, r=new: r, patched, count=1)
            if n != 1:
                ok = False
                break
        rec = {"id": cand["id"], "why": cand["why"], "n_ops": len(cand["ops"])}
        if not ok:
            rec.update(verdict="ANCHOR_MISS",
                       note="锚点缺失 ⇒ fail-closed（记「未测到」，禁读作「无缺陷」）")
            out["attempts"].append(rec)
            continue
        tmp = tempfile.mkdtemp(prefix="r641mf-")
        dst = os.path.join(tmp, "t")
        try:
            shutil.copytree(os.path.join(SNAP, run, "g1"), dst)
            io.open(os.path.join(dst, "games", "wythoff.py"), "w", encoding="utf-8").write(patched)
            after = fam_scores(dst, cases)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        others = ("life", "sub", "nim")
        others_unchanged = all(after[f] == base[f] for f in others)
        rec.update(target_before=base["wythoff"], target_after=after["wythoff"],
                   others_before={f: base[f] for f in others},
                   others_after={f: after[f] for f in others},
                   others_unchanged=others_unchanged,
                   verdict=("CONFIRMED" if (after["wythoff"] == 15 and others_unchanged)
                            else ("PARTIAL" if after["wythoff"] > base["wythoff"] else "NO_EFFECT")))
        out["attempts"].append(rec)
    tmp = tempfile.mkdtemp(prefix="r641nc-")
    dst = os.path.join(tmp, "t")
    try:
        shutil.copytree(os.path.join(SNAP, run, "g1"), dst)
        io.open(os.path.join(dst, "games", "wythoff.py"), "w", encoding="utf-8").write(raw)
        nc = fam_scores(dst, cases)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out["null_rewrite_negctl"] = {"families": nc, "identical_to_base": nc == base,
                                  "still_red": nc["wythoff"] < 15, "pass": nc == base}
    out["confirmed"] = [a["id"] for a in out["attempts"] if a.get("verdict") == "CONFIRMED"]
    out["state"] = "能力缺陷（产物侧，行级定因）" if out["confirmed"] else "未测到"
    return out


# ---------------- J5 分辨率条款（**见证式**：非 crash 型 mutant，构造上不抛异常）
def resolution_clause(cases):
    """采样面（15 例）⊂ 规格面（25×25=625 格）且为**稀疏**子集 ⇒ 存在「采样面 15/15 ∧ 规格面判红」的变异体。

    见证构造（不作弊解，而是**采样面专用解**）：命中采样位置的答案（取自采样面）直接返回；
    其余位置一律给**良构但错**的答案 ⇒ 采样面必然全绿、规格面必然大面积红，且不可能抛异常。
    """
    wy = [c for c in cases if c["game"] == "wythoff"]
    ans = {c["stdin"].split()[0] + " " + c["stdin"].split()[1]: c["expected_stdout"].strip() for c in wy}

    def cheat(text, drop=None):
        key = " ".join(text.split()[:2])
        if key in ans and key != drop:
            return ans[key]
        a, b = (int(x) for x in text.split()[:2])
        return "LOSE" if not ORC.LOSING[a][b] else "WIN 1 0"

    def sample_ok(fn):
        return sum(1 for c in wy if fn(c["stdin"]).strip() == c["expected_stdout"].strip())

    grid_bad, grid_n = 0, 0
    for a in range(1, 26):
        for b in range(1, 26):
            grid_n += 1
            if cheat("%d %d" % (a, b)).strip() != ORC.solve("%d %d" % (a, b)).strip():
                grid_bad += 1
    sm = sample_ok(cheat)
    sm_rev = sample_ok(lambda t: cheat(t, drop="6 10"))
    return {
        "clause": "采样面（15 例）是规格面（25×25=625 格）的**稀疏子集** ⇒ 采样面全绿不构成规格面通过",
        "witness": "采样面专用解（命中采样位置返回采样答案；其余位置返回良构错答案）",
        "sample_face": "%d/%d" % (sm, len(wy)),
        "grid_face_violations": "%d/%d" % (grid_bad, grid_n),
        "positive": (sm == len(wy)) and grid_bad > 0,
        "reverse_control": {
            "witness": "同一见证**去掉 1 个采样位置**（(6,10) 落回错答案分支）",
            "sample_face": "%d/%d" % (sm_rev, len(wy)),
            "sample_face_red": sm_rev < len(wy),
            "pass": sm_rev < len(wy),
        },
        "pass": (sm == len(wy)) and grid_bad > 0 and sm_rev < len(wy),
    }


def discover():
    return [("%s/%s" % (w, s), os.path.join(SNAP, w, s, "g1")) for w in WINS for s in SUBS]


def replay(cases):
    per_run, per_case = {}, {}
    for run, tree in discover():
        recs = []
        for idx, c in enumerate(cases):
            rc, out, _ = run_probe(tree, c["game"], c["stdin"])
            if c["game"] == "wythoff":
                tag, detail = classify_case(rc, out, c)
            else:
                tag, detail = (("OK", "") if (rc == 0 and
                               out.strip("\n") == c["expected_stdout"].strip("\n")) else ("MISMATCH", ""))
            recs.append({"idx": idx, "game": c["game"], "vis": c["vis"], "stdin": c["stdin"].strip(),
                         "exp": c["expected_stdout"].strip(), "got": out.strip("\n")[:40], "rc": rc,
                         "tag": tag, "detail": detail})
        per_case[run] = recs
        per_run[run] = {"pass": sum(1 for r in recs if r["tag"] == "OK"), "n": len(recs),
                        "tags": {t: sum(1 for r in recs if r["tag"] == t)
                                 for t in sorted({r["tag"] for r in recs})},
                        "fails": [r for r in recs if r["tag"] != "OK"]}
    return per_run, per_case


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    os.makedirs(OUTDIR, exist_ok=True)
    cases = load_cases()
    res = {"round": "R641", "kind": "readonly-attribution+instrument-face",
           "instrument": {"file": "eval/rover/r641/attrib_r641.py",
                          "sha256": sha256(os.path.abspath(__file__)),
                          "cases_sha256": sha256(CASES)},
           "J0": oracle_control(cases)}
    exp, meta = expectations()
    res["expectations"] = {"n": len(exp) if exp else 0, "meta": meta, "table": exp or {}}
    if exp is None:
        save(res, a.out)
        print("EXPECTATIONS_FAILED rc=%s %s" % (meta["rc"], meta["why"]))
        return meta["rc"]
    cache = jload(CACHE_REPLAY)
    if cache and cache.get("cases_sha256") == sha256(CASES):
        per_run, per_case = cache["per_run"], cache["per_case"]
        res["J2_note"] = "replay 取自断点续跑缓存（同一 cases sha）"
        print("[cache] replay reused", flush=True)
    else:
        per_run, per_case = replay(cases)
        save({"cases_sha256": sha256(CASES), "per_run": per_run, "per_case": per_case}, CACHE_REPLAY)
    res["per_run"] = per_run
    tot = sum(v["n"] for v in per_run.values())
    res["J2_conservation"] = {"total": tot, "expected": len(per_run) * len(cases),
                              "per_run_ok": all(v["n"] == len(cases) for v in per_run.values())}
    res["J2_conservation"]["pass"] = (tot == len(per_run) * len(cases)
                                      and res["J2_conservation"]["per_run_ok"])
    mism = [{"run": r, "expect_pass_run": e["pass_run"],
             "replay_pass": per_run[r]["pass"] == per_run[r]["n"]}
            for r, e in exp.items() if e["pass_run"] != (per_run[r]["pass"] == per_run[r]["n"])]
    res["J1_replay_cross_validation"] = {"mismatch": mism, "pass": not mism}
    fy = {}
    for r, recs in per_case.items():
        f = [x for x in recs if x["game"] == "wythoff" and x["tag"] != "OK"]
        fy[r] = {"n_fail": len(f),
                 "tags": {t: sum(1 for x in f if x["tag"] == t) for t in sorted({x["tag"] for x in f})},
                 "frame_transpose_examples": [x["detail"] for x in f if x["tag"] == "FRAME_TRANSPOSE"][:3]}
    res["J3_per_case_attribution"] = fy
    res["J3_note"] = ("帧感知分类：`FRAME_TRANSPOSE` = 输出着法的**转置**为必胜着法 ⇒ 表示面缺陷；"
                      "R640 判据器把这批误标为 `nonwinning_move`（帧不感知）")
    save(res, a.out)
    print("[save] post-replay", flush=True)

    j4 = jload(CACHE_J4)
    if j4 and j4.get("cases_sha256") == sha256(CASES):
        res["J4_line_level_minfix"] = j4["blocks"]
        print("[cache] J4 reused", flush=True)
    else:
        targets = ["w237/agentP-r3", "w238/agentP-r3", "w239/agentP-r1", "w239/agentP-r2", "w239/codex"]
        blocks = []
        for i, r in enumerate(targets):
            blocks.append(minfix_run(r, cases))
            save({"cases_sha256": sha256(CASES), "blocks": blocks, "partial": i + 1 < len(targets),
                  "n_targets": len(targets)}, CACHE_J4)
            print("[save] J4 %d/%d %s %s" % (i + 1, len(targets), r,
                                             blocks[-1]["confirmed"]), flush=True)
        res["J4_line_level_minfix"] = blocks
    res["J4_summary"] = {
        "n_targets": len(res["J4_line_level_minfix"]),
        "n_confirmed": sum(1 for x in res["J4_line_level_minfix"] if x["confirmed"]),
        "n_anchor_miss": sum(1 for x in res["J4_line_level_minfix"]
                             for at in x["attempts"] if at.get("verdict") == "ANCHOR_MISS"),
        "null_negctl_pass": all(x["null_rewrite_negctl"]["pass"] for x in res["J4_line_level_minfix"])}
    save(res, a.out)
    print("[save] post-J4", flush=True)

    res["J5_resolution_clause"] = resolution_clause(cases)
    save(res, a.out)
    print("[save] post-J5", flush=True)

    per_run2, _ = replay(cases)
    res["J8_determinism"] = {"pairs": [{"run": r, "identical": per_run[r] == per_run2[r]} for r in per_run],
                             "pass": all(per_run[r] == per_run2[r] for r in per_run)}
    sigs = sorted({"|".join("%s=%s" % (k, x) for k, x in sorted(v["tags"].items())) + ":%d" % v["pass"]
                   for v in per_run.values()})
    res["J9_non_triviality"] = {"distinct_signatures": len(sigs), "n_runs": len(per_run),
                                "pass": len(sigs) >= 2}
    save(res, a.out)
    print("J0", res["J0"]["positive"], "mutant_teeth", res["J0"]["mutant_teeth"])
    print("J1 mismatch", len(mism), "J2", tot, res["J2_conservation"]["pass"])
    print("J4 confirmed", res["J4_summary"]["n_confirmed"], "/", res["J4_summary"]["n_targets"],
          "anchor_miss", res["J4_summary"]["n_anchor_miss"], "null_nc", res["J4_summary"]["null_negctl_pass"])
    print("J5", res["J5_resolution_clause"]["sample_face"],
          res["J5_resolution_clause"]["grid_face_violations"],
          "rev_red", res["J5_resolution_clause"]["reverse_control"]["sample_face_red"])
    print("J8", res["J8_determinism"]["pass"], "J9", res["J9_non_triviality"]["distinct_signatures"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
