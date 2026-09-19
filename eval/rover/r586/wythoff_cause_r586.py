#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R586 · wythoff 族**只读**定因 (零产品改动 / 零新夹具 / 零远端).

输入面 (全部为已冻结、已登记件, 只读):
  · 冻结语料 `eval/rover/r560/cases/cases-r521.json` (sha256 270128eb…, R519/R521 同源)
  · 已落盘产物快照 `eval/rover/r560/snapshots/<win>/<arm>/g1/**` (R560 六窗 × 三臂)
工序 (对齐 skill: 判分必须对**副本**, 不污染冻结快照树):
  逐 (窗, 臂) 复制快照到临时目录 -> 对每例 `python3 -m games wythoff` (stdin=用例输入)
  -> 逐字节比对 stdout (尾换行归一) -> 落 (got, exp) 原始读数
定因分类 (机械可判, 无人工口径):
  LOSE_FOR_WIN     期望 WIN 但产出 LOSE           => 胜负判定错
  WIN_FOR_LOSE     期望 LOSE 但产出 WIN           => 胜负判定错
  MOVE_NOT_COLD    期望 WIN, 产出 WIN 且可解析为「移除对」但落点非冷点 => 冷点集构造错
  MOVE_SHAPE       期望 WIN, 产出 WIN 但形态不可解析 (字段数/非整数)
  EMPTY_OR_ERROR   空输出 / 非零退出
  OTHER            其余
输出: eval/rover/r586/wythoff-cause-r586.json  (含逐例原始 got/exp + 分类 + 跨窗摆动读数)
用法: python3 eval/rover/r586/wythoff_cause_r586.py [--out <path>] [--copies <dir>]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
CASES = os.path.join(REPO, "eval/rover/r586/cases/cases-r521.json")   # 逐字节复制件 (sha 270128eb…, 与 r560 同件)
# 窗口 -> (轮次目录, 臂名) —— 两轮快照目录各自独立, 臂名随轮 (R559B0/R560B0 …)
WINDOW_MAP = {
    "w157": ("r586", ["C1", "agentD-r1", "agentD-r2", "agentD-r3"]),
    "w158": ("r586", ["C1", "agentD-r1", "agentD-r2", "agentD-r3"]),
    "w159": ("r586", ["C1", "agentD-r1", "agentD-r2", "agentD-r3"]),
}
WINDOWS = os.environ.get("R586_WINDOWS", ",".join(WINDOW_MAP)).split(",")
ARMS = ["C1", "agentD-r1", "agentD-r2", "agentD-r3"]


def norm(s: str) -> str:
    return s.replace("\r\n", "\n").rstrip("\n")


def cold_set_phi(limit: int):
    """独立冷点集 (phi 差值序 + 终端 (0,0)) —— 分类用, 不参与判分."""
    out, k = {(0, 0)}, 1
    while True:
        a = int(k * ((5 ** 0.5 + 1) / 2))
        b = a + k
        if a > limit and b > limit:
            break
        out.add((a, b))
        k += 1
    return out


def cold_set_brute(L: int = 25):
    """冷点集**暴力递推**(与被测零共享算法; 交叉校验用): 按「和」递增序 ⇒ 后继必已算过."""
    memo = {}
    for s in range(0, 2 * L + 1):
        for a in range(0, s + 1):
            b = s - a
            if a > L or b > L:
                continue
            cold = True
            for i in range(a + 1):
                for j in range(b + 1):
                    if i == 0 and j == 0:
                        continue
                    if not ((i > 0 and j == 0) or (i == 0 and j > 0) or i == j):
                        continue  # 题面约束: 单堆任意 / 双堆等量
                    t = (max(a - i, b - j), min(a - i, b - j))
                    if memo.get(t) is True:
                        cold = False
                        break
                if not cold:
                    break
            memo[(max(a, b), min(a, b))] = cold
    return {k for k, v in memo.items() if v}


def legal_moves(a: int, b: int, cold):
    """题面逐字: (i) 任意一堆任意正数 (ii) 两堆等量正数; 返回 [(i,j)] 全部**致胜**着法."""
    out = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i > 0 and j == 0) or (i == 0 and j > 0) or i == j):
                continue
            t = (max(a - i, b - j), min(a - i, b - j))
            if t in cold:
                out.append((i, j))
    return out


def is_cold(a: int, b: int, limit: int) -> bool:
    if a > b:
        a, b = b, a
    return (a, b) in cold_set_phi(limit)


def parse_move(s: str):
    parts = s.split()
    if len(parts) != 3 or parts[0] != "WIN":
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


def classify(case, got: str, rc: int, ora):
    exp = norm(case["expected_stdout"])
    g = norm(got)
    if rc != 0:
        return "EMPTY_OR_ERROR", None
    if not g.strip():
        return "EMPTY_OR_ERROR", None
    a, b = [int(x) for x in case["stdin"].split()]
    cold = ora["cold"]
    exp_win = exp.startswith("WIN")
    got_win = g.startswith("WIN")
    if exp_win and not got_win:
        return "LOSE_FOR_WIN", None
    if (not exp_win) and got_win:
        return "WIN_FOR_LOSE", None
    if exp_win:
        mv = parse_move(g)
        if mv is None:
            return "MOVE_SHAPE", None
        i, j = mv
        if i < 0 or j < 0 or (i == 0 and j == 0):
            return "MOVE_SHAPE", "zero_or_negative(%d,%d)" % (i, j)
        legal = (i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)
        if not legal or i > a or j > b:
            return "MOVE_ILLEGAL", "removals(%d,%d)" % (i, j)
        t = (max(a - i, b - j), min(a - i, b - j))
        if t not in cold:
            return "MOVE_NOT_COLD", "target(%d,%d)" % t
        lm = ora["lexmin"]["%d,%d" % (a, b)]
        if (i, j) != lm:
            return "MOVE_NOT_LEXMIN", "got(%d,%d) lexmin(%s)" % (i, j, lm)
        return "OK", "target(%d,%d)" % t
    # exp = LOSE: 词标不符 (实测形态: 直接吐出冷点坐标而不给 LOSE 词标) ⇒ 单列, 禁与 OK 混淆
    if g != exp:
        return "LOSE_LABEL_MISMATCH", "got_text(%r)" % g[:24]
    return "OK", None


def build_oracle(allc):
    """独立 oracle: 冷点集暴力递推 ∧ phi 序交叉校验 ⇒ 逐题 lexmin 期望值 (与被测零共享实现)."""
    cold = cold_set_brute(25)
    phi = {(max(x), min(x)) for x in cold_set_phi(25) if max(x) <= 25}
    cases = [c for c in allc if c["game"] == "wythoff"]
    lex, audit = {}, []
    for i, c in enumerate(cases):
        a, b = [int(x) for x in c["stdin"].split()]
        mv = legal_moves(a, b, cold)
        key = "%d,%d" % (a, b)
        lex[key] = min(mv) if mv else None
        exp = norm(c["expected_stdout"])
        want = "LOSE" if ((max(a, b), min(a, b)) in cold) else ("WIN %d %d" % lex[key] if lex[key] else None)
        audit.append({"idx": i, "stdin": c["stdin"].strip(), "expected": exp, "oracle": want,
                      "agrees": exp == want, "n_winning_moves": len(mv)})
    return {"cold": cold, "lexmin": lex,
            "phi_vs_brute_equal": (phi == cold),
            "phi_only": sorted(phi - cold), "brute_only": sorted(cold - phi),
            "fixture_audit": audit, "fixture_agrees": all(x["agrees"] for x in audit)}


def run_arm_copy(win: str, arm: str, copies: str, cases, ora, timeout: int = 60, only_idx=None):
    rk = WINDOW_MAP[win][0]
    src = os.path.join(REPO, "eval/rover/%s/snapshots" % rk, win, arm, "g1")
    dst = os.path.join(copies, "%s-%s" % (win, arm))
    if not os.path.isdir(src):
        return None, "missing_snapshot:%s" % src
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": dst,
           "PYTHONPATH": dst, "PYTHONDONTWRITEBYTECODE": "1"}
    out = []
    for i, c in enumerate(cases):
        if only_idx is not None and i not in only_idx:
            continue
        try:
            p = subprocess.run([sys.executable, "-m", "games", c["game"]], input=c["stdin"],
                               capture_output=True, text=True, cwd=dst, env=env, timeout=timeout)
            got, rc = p.stdout, p.returncode
        except Exception as e:  # noqa: BLE001
            got, rc = "", -1
            out.append({"idx": i, "name": "%s#%02d-%s" % (c["game"], i, c["vis"]), "class": "EMPTY_OR_ERROR",
                        "timeout_s": timeout,
                        "why": "%s: %s" % (type(e).__name__, str(e)[:80]), "got": "", "exp": norm(c["expected_stdout"])})
            continue
        klass, detail = classify(c, got, rc, ora)
        out.append({"idx": i, "name": "%s#%02d-%s" % (c["game"], i, c["vis"]), "class": klass,
                    "timeout_s": timeout,
                    "match": (norm(got) == norm(c["expected_stdout"])),
                    "why": detail or "", "got": norm(got)[:80], "exp": norm(c["expected_stdout"])[:80],
                    "rc": rc})
    return out, None


def classifier_selftest(allc, ora):
    """判据器正控/负控 (对**副本语义**判分, 不触碰快照树): 期望值必须全 OK; 注入变异必须非 OK."""
    cases = [c for c in allc if c["game"] == "wythoff"]
    pos = [classify(c, c["expected_stdout"], 0, ora)[0] for c in cases]
    muts = []
    for i, c in enumerate(cases):
        exp = norm(c["expected_stdout"])
        a, b = [int(x) for x in c["stdin"].split()]
        if exp.startswith("WIN"):
            muts.append(("lose_swap", classify(c, "LOSE", 0, ora)[0]))
            muts.append(("shape", classify(c, "WIN x y", 0, ora)[0]))
            muts.append(("overflow", classify(c, "WIN 99 99", 0, ora)[0]))
            muts.append(("illegal_both", classify(c, "WIN %d %d" % (1, 2 if a > 1 else 3), 0, ora)[0]))
        else:
            muts.append(("win_swap", classify(c, "WIN 1 1", 0, ora)[0]))
        # 承重负控: 合法单堆招法但落点非冷点 -> 必须判 MOVE_NOT_COLD (本族主失效模式)
        if exp.startswith("WIN"):
            for rem in ((1, 0), (0, 1)):
                na, nb = a - rem[0], b - rem[1]
                if na >= 0 and nb >= 0 and (max(na, nb), min(na, nb)) not in ora["cold"]:
                    muts.append(("wrong_cold", classify(c, "WIN %d %d" % rem, 0, ora)[0]))
                    break
    bad = [x for x in pos if x != "OK"]
    hollow = [m for m in muts if m[1] == "OK"]
    return {"positive_ok": sum(1 for x in pos if x == "OK"), "positive_n": len(pos),
            "positive_bad": bad, "mutants_n": len(muts), "mutants_ok_wrongly": hollow,
            "has_teeth": (not bad) and (not hollow),
            "fixture_agrees_with_oracle": ora["fixture_agrees"],
            "phi_vs_brute_equal": ora["phi_vs_brute_equal"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r586/wythoff-cause-r586.json"))
    ap.add_argument("--copies", default="/tmp/r586/copies")
    ap.add_argument("--reclassify", default=None,
                    help="离线重算分类 (不重跑被测): 读既有读数件的 raw_rows 重算 class (纯一致性重判)")
    ap.add_argument("--timeout", type=int, default=60, help="逐例截止秒 (默认 60 = 产品侧同口径)")
    ap.add_argument("--only-idx", default=None,
                    help="逗号分隔的族内下标白名单 (超时例分离实验用: 只重跑基跑失败的例)")
    a = ap.parse_args()
    only_idx = None if a.only_idx is None else {int(x) for x in a.only_idx.split(",") if x.strip() != ""}
    os.makedirs(a.copies, exist_ok=True)
    allc = json.load(open(CASES, encoding="utf-8"))
    cases = [c for c in allc if c["game"] == "wythoff"]
    ora = build_oracle(allc)
    if a.reclassify:
        d = json.load(open(a.reclassify, encoding="utf-8"))
        n_chg = 0
        for key, rows in d["raw_rows"].items():
            for r in rows:
                c = cases[r["idx"]]
                k, why = classify(c, r["got"], r.get("rc", 0), ora)
                # 读数件里 got/exp 已按 ≤80 字符截断 (wythoff 输出恒 ≤12 字符 ⇒ 无损); 以截断串重判
                exp_txt = r["exp"]
                r["match"] = (r["got"] == exp_txt)
                if k != r["class"] or (why or "") != (r["why"] or ""):
                    n_chg += 1
                r["class"], r["why"] = k, why or ""
        import collections as _c
        for key, rows in d["raw_rows"].items():
            s = d["per_arm_window"][key]
            s["classes"] = dict(_c.Counter(x["class"] for x in rows if not x["match"]))
            s["fail_idx"] = [x["idx"] for x in rows if not x["match"]]
            s["n_pass"] = sum(1 for x in rows if x["match"])
            s["match_vs_class_disagree"] = [x["idx"] for x in rows if x["match"] != (x["class"] == "OK")]
        d["reclassify"] = {"n_class_changed": n_chg, "note": "离线重判 (无被测执行); 判分主判据 = 逐字节"}
        json.dump(d, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps({"reclassify": n_chg, "out": a.out,
                          "fail_classes_total": dict(_c.Counter(x["class"] for rows in d["raw_rows"].values()
                                                                for x in rows if not x["match"])),
                          "disagree": {k: v["match_vs_class_disagree"] for k, v in d["per_arm_window"].items()
                                       if v["match_vs_class_disagree"]}}, ensure_ascii=False))
        return 0
    stf = classifier_selftest(allc, ora)
    if not (ora["phi_vs_brute_equal"] and ora["fixture_agrees"] and stf["has_teeth"]):
        print(json.dumps({"FATAL": "oracle/selftest fail-closed", "selftest": stf,
                          "phi_only": ora["phi_only"], "brute_only": ora["brute_only"],
                          "fixture_disagree": [x for x in ora["fixture_audit"] if not x["agrees"]]}, ensure_ascii=False))
        return 2
    res, errs = {}, {}
    for win in WINDOWS:
        for arm in WINDOW_MAP[win][1]:
            rows, err = run_arm_copy(win, arm, a.copies, cases, ora, timeout=a.timeout, only_idx=only_idx)
            if err:
                errs["%s|%s" % (win, arm)] = err
                continue
            res["%s|%s" % (win, arm)] = rows
    # ---- 汇总 ----
    import collections
    summary = {}
    for key, rows in res.items():
        cls = collections.Counter(r["class"] for r in rows if not r["match"])
        summary[key] = {"classes": dict(cls), "fail_idx": [r["idx"] for r in rows if not r["match"]],
                        "n_pass": sum(1 for r in rows if r["match"]),
                        "match_vs_class_disagree": [r["idx"] for r in rows if r["match"] != (r["class"] == "OK")]}
    # 逐例跨窗摆动 (同臂内, 该例是否在窗集里既过又败) —— 仅在全量跑时计算 (下标过滤跑时行集不完整)
    osc = {}
    if only_idx is None:
      for arm in ARMS:
        wins = [w for w in WINDOWS if arm in WINDOW_MAP[w][1]]
        if not wins:
            continue
        for i in range(len(cases)):
            st = [res["%s|%s" % (w, arm)][i]["class"] if "%s|%s" % (w, arm) in res else "NA" for w in wins]
            osc["%s#%02d" % (arm, i)] = {"windows": wins, "states": st,
                                         "oscillates": len({x for x in st if x != "OK"}) > 0 and any(x == "OK" for x in st)}
    # 跨窗同例产出变体数 (非确定性直接读数) —— 同上, 仅全量跑
    variants = {}
    if only_idx is None:
      for arm in ARMS:
        wins = [w for w in WINDOWS if arm in WINDOW_MAP[w][1]]
        if not wins:
            continue
        v = {}
        for i in range(len(cases)):
            gots = {res["%s|%s" % (w, arm)][i]["got"] for w in wins if "%s|%s" % (w, arm) in res}
            v[i] = sorted(gots)
        variants[arm] = v
    # 冷点集探测: 每个 MOVE_NOT_COLD 的落点 k 差 (int(phi*min) 型错法的指纹)
    fingerprint = {}
    for key, rows in res.items():
        for r in rows:
            if r["class"] in ("MOVE_NOT_COLD", "MOVE_SHAPE") and r["why"].startswith("target"):
                fingerprint.setdefault(key, []).append({"idx": r["idx"], "got": r["got"], "exp": r["exp"], "why": r["why"]})
    out = {"round": "R586", "instrument": "wythoff_cause_r586.py",
           "mode": "read_only (零产品改动 / 零新夹具 / 零远端; 快照副本上重放冻结语料)",
           "corpus": {"path": CASES, "n_wythoff": len(cases)},
           "windows": WINDOWS, "arms": ARMS,
           "primary_criterion": "逐字节比对 stdout (与 run_cases_r521.py 同口径); class = 语义定因 (仅对未匹配项)",
           "oracle": {"n_winning_moves_per_case": [x["n_winning_moves"] for x in ora["fixture_audit"]],
                      "fixture_audit": ora["fixture_audit"],
                      "note": "oracle 与被测零共享: 冷点集=暴力递推(按和递增序) ∧ phi 序交叉校验; 题面约束(单堆任意/双堆等量) + 字典序最小"},
           "classifier_selftest": stf,
           "errors": errs, "per_arm_window": summary, "per_case_oscillation": osc,
           "per_case_got_variants": variants, "not_cold_detail": fingerprint,
           "raw_rows": res}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"out": a.out, "errors": errs, "selftest": {"pos": "%d/%d" % (stf["positive_ok"], stf["positive_n"]),
                      "mutants_naive_ok": len(stf["mutants_ok_wrongly"]), "mutants_n": stf["mutants_n"], "teeth": stf["has_teeth"]},
                      "pass_by_key": {k: v["n_pass"] for k, v in sorted(summary.items())},
                      "disagree": {k: v["match_vs_class_disagree"] for k, v in summary.items() if v["match_vs_class_disagree"]},
                      "fail_classes_total": dict(collections.Counter(
                          r["class"] for rows in res.values() for r in rows if not r["match"]))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
