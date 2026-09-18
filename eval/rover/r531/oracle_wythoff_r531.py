#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R531 遗留定因器具: wythoff 族**非同源**独立 oracle（手写博弈 DP, 不调用夹具生成器）。

动机: R531 w1 四臂读数里 F1 出现「A0-off 56/58 · A1-on 56/58 · A2-merge 58/58 · C-codex 58/58」。
必须先判定这 2 例失败是**夹具缺陷**还是**能力缺陷**（R512 教训: p4 题面缺句 ⇒ 两侧同败 ⇒ 判据无区分力）。
判据法: 用与夹具截然不同的算法（自底向上 P/N 位 DP + 暴力枚举合法着法）重算规范答案,
       与 ① 冻结用例 expected_stdout ② 各臂冻结快照实跑输出 三方比对。

题面逐字契约（eval/rover/r531/taskset-r531.json → g1.prompt → ### 游戏 `wythoff`）:
  读入一行两个整数 a b (1..25); 每次可取 (i) 任一堆任意正数 或 (ii) 两堆同数;
  输出 LOSE（先手必败）否则 `WIN i j` —— i = 从第一堆取走数, j = 从第二堆取走数,
  (i, j) 在全部必胜着法中按**字典序最小**（先比 i 再比 j; i,j>=0 且不同时为 0）。

用法: python3 eval/rover/r531/oracle_wythoff_r531.py [--json <out>]
rc: 0 = 冻结用例与独立 oracle 完全一致（⇒ 失败属能力面）; 1 = 存在不一致（⇒ 疑夹具缺陷, 逐条点名）
"""
import argparse
import json
import os
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
ROUND = "R531"
SNAPWIN = "w1"  # 由 --window 覆盖: 冻结快照窗口 eval/rover/r531/snapshots/<win>/


def p_positions(n=25):
    """自底向上 P/N 位判定: P = 轮到走的人必败。返回 {(a,b): bool_is_P}（a<=b 规范化键）。"""
    is_p = {}
    for a in range(n + 1):
        for b in range(a, n + 1):
            win = False
            # (i) 从第一堆取 x>0
            for x in range(1, a + 1):
                k = (min(a - x, b), max(a - x, b))
                if is_p.get(k, k == (0, 0)):
                    win = True
                    break
            if not win:
                # (i) 从第二堆取 y>0
                for y in range(1, b + 1):
                    k = (min(a, b - y), max(a, b - y))
                    if is_p.get(k, k == (0, 0)):
                        win = True
                        break
            if not win:
                # (ii) 两堆同取 t>0
                for t in range(1, a + 1):
                    k = (a - t, b - t)
                    if is_p.get(k, k == (0, 0)):
                        win = True
                        break
            is_p[(a, b)] = not win
    return is_p


def canonical_move(a, b, is_p):
    """题面契约: 字典序最小 (i, j)。暴力枚举全部合法必胜着法后取 min（不预设启发式）。"""
    cands = [(i, 0) for i in range(1, a + 1)]
    cands += [(0, j) for j in range(1, b + 1)]
    cands += [(t, t) for t in range(1, min(a, b) + 1)]
    best = None
    for (i, j) in cands:
        na, nb = a - i, b - j
        k = (min(na, nb), max(na, nb))
        if is_p.get(k, k == (0, 0)):
            if best is None or (i, j) < best:
                best = (i, j)
    return best


def classify(a, b, out):
    """把一条臂输出归类: canonical / legal_but_not_canonical / illegal / wrong_lose / malformed。"""
    want = solve("%d %d" % (a, b))
    if out == want:
        return "canonical"
    if out == "LOSE":
        return "wrong_lose"
    if not out.startswith("WIN "):
        return "malformed"
    try:
        i, j = (int(x) for x in out.split()[1:3])
    except (ValueError, IndexError):
        return "malformed"
    if i < 0 or j < 0 or i > a or j > b or (i == 0 and j == 0) or (i and j and i != j):
        return "illegal_move"
    k = (min(a - i, b - j), max(a - i, b - j))
    if P.get(k, k == (0, 0)):
        return "legal_but_not_canonical"
    return "non_winning_move"


def solve(text):
    a, b = (int(x) for x in text.split())
    is_p = P
    key = (min(a, b), max(a, b))
    if is_p[key]:
        return "LOSE"
    i, j = canonical_move(a, b, is_p)
    return "WIN %d %d" % (i, j)


def run_case(wd, stdin_text):
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": wd,
           "PYTHONPATH": wd, "PYTHONDONTWRITEBYTECODE": "1"}
    p = subprocess.run([sys.executable, "-B", "-m", "games", "wythoff"], input=stdin_text,
                       capture_output=True, text=True, timeout=60, cwd=wd, env=env)
    return p.returncode, p.stdout.strip("\n")


def compare(cases, wy, arms):
    """对给定用例集重算 oracle 并跑各臂 → (rows, bad_fixture, per_arm)。"""
    rows = []
    bad_fixture = []
    for i, c in wy:
        exp = c["expected_stdout"].strip("\n")
        mine = solve(c["stdin"])
        row = {"case": i, "vis": c["vis"], "stdin": c["stdin"].strip(),
               "expected": exp, "oracle": mine, "oracle_agrees": mine == exp, "arms": {}}
        if mine != exp:
            bad_fixture.append({"case": i, "stdin": row["stdin"], "expected": exp, "oracle": mine})
        for arm in arms:
            wd = os.path.join(REPO, "eval/rover", SNAPROUND, "snapshots", SNAPWIN, arm, "g1")
            if not os.path.isdir(wd):
                row["arms"][arm] = {"absent": True}
                continue
            rc, got = run_case(wd, c["stdin"])
            a_, b_ = (int(x) for x in c["stdin"].split())
            row["arms"][arm] = {"rc": rc, "out": got, "match": got == exp,
                                "class": classify(a_, b_, got)}
        rows.append(row)
    per_arm = {}
    for arm in arms:
        ok = sum(1 for r in rows if r["arms"].get(arm, {}).get("match"))
        present = sum(1 for r in rows if not r["arms"].get(arm, {}).get("absent"))
        per_arm[arm] = "%d/%d" % (ok, present)
    return rows, bad_fixture, per_arm


def neg_control(cases, wy, arms):
    """NC1: 把某例期望篡改成错答案 ⇒ 不一致检测器必须触发 (防「恒真一致」)。
    NC2: 把一个**非法着法** (i≠j 且 i,j>0, 题面只允许单堆取或等量双取) 交给 classify ⇒ 必须判 illegal_move。"""
    mut = json.loads(json.dumps(cases))
    ci, _c = wy[0]
    mut[ci]["expected_stdout"] = "LOSE" if solve(_c["stdin"]) != "LOSE" else "WIN 0 0"
    wy_mut = [(ci, mut[ci])]
    _rows, bad, _pa = compare(mut, wy_mut, arms[:1])
    nc1 = len(bad) >= 1
    # 找一个存在「不等量双取」非法着法的用例 (i≠j 且 i,j>0 且界内)
    probe = None
    for _i, _c2 in wy:
        _a, _b = (int(x) for x in _c2["stdin"].split())
        if _a >= 1 and _b >= 2:
            probe = (_a, _b, "WIN 1 2")
            break
        if _a >= 2 and _b >= 1:
            probe = (_a, _b, "WIN 2 1")
            break
    if probe is None:
        print("NC2 跳过: 无用例可构造界内非法着法")
        nc2 = False
        cls = "n/a"
    else:
        cls = classify(probe[0], probe[1], probe[2])
        nc2 = cls == "illegal_move"
    print("NC1 篡改期望 ⇒ 不一致被检出: %s (disagreements=%d)" % (nc1, len(bad)))
    print("NC2 非法着法 %s @(%s,%s) ⇒ classify=%s (须 illegal_move): %s"
          % (probe[2] if probe else "-", probe[0] if probe else "-", probe[1] if probe else "-", cls, nc2))
    print("NEG_CONTROL_OK=%s" % (nc1 and nc2))
    return 0 if (nc1 and nc2) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", default=ROUND)
    ap.add_argument("--window", default="w1", help="冻结快照窗口 (snapshots/<win>)")
    ap.add_argument("--arms", default=None, help="逗号分隔的臂目录名; 缺省= r531 冻结臂集(保形)")
    ap.add_argument("--cases", default=None, help="用例JSON; 缺省= r531/cases/cases-r521.json(保形)")
    ap.add_argument("--json", default=None)
    ap.add_argument("--neg-control", action="store_true")
    a = ap.parse_args()

    global P, SNAPWIN, SNAPROUND
    P = p_positions(25)
    SNAPWIN = a.window
    SNAPROUND = "r" + (a.round[1:] if a.round[:1] in ("r", "R") else a.round)

    cases_path = a.cases or os.path.join(REPO, "eval/rover/r531/cases/cases-r521.json")
    cases = json.load(open(cases_path, encoding="utf-8"))
    wy = [(i, c) for i, c in enumerate(cases) if c["game"] == "wythoff"]

    arms = a.arms.split(",") if a.arms else ["agentA0-off", "agentA1-on", "agentA2-merge", "codex"]
    if a.neg_control:
        return neg_control(cases, wy, arms)

    rows, bad_fixture, per_arm = compare(cases, wy, arms)

    result = {
        "round": a.round,
        "window": SNAPWIN,
        "instrument": "eval/rover/r531/oracle_wythoff_r531.py",
        "method": "独立手写 P/N 位 DP + 暴力枚举合法着法（与夹具生成器非同源）",
        "cases_path": os.path.relpath(cases_path, REPO),
        "wythoff_cases": len(wy),
        "fixture_agrees_with_oracle": not bad_fixture,
        "fixture_disagreements": bad_fixture,
        "per_arm_pass": per_arm,
        "rows": rows,
    }

    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=1)

    print("wythoff 用例数 = %d" % len(wy))
    print("冻结用例 vs 独立 oracle: %s" % ("完全一致" if not bad_fixture else "不一致 %d 条" % len(bad_fixture)))
    for b in bad_fixture:
        print("  DISAGREE case#%d stdin=%s expected=%s oracle=%s" % (b["case"], b["stdin"], b["expected"], b["oracle"]))
    for arm in arms:
        print("  %-14s %s" % (arm, per_arm[arm]))
    for r in rows:
        if not all(r["arms"].get(arm, {}).get("match") for arm in arms):
            print("case#%d stdin=%s vis=%s exp=%s" % (r["case"], r["stdin"], r["vis"], r["expected"]))
            for arm in arms:
                d = r["arms"][arm]
                print("   %-14s %s" % (arm, d.get("out", d)))
    return 0 if not bad_fixture else 1


if __name__ == "__main__":
    sys.exit(main())
