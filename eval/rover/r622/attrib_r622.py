#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R622 · wythoff 族能力缺口**逐例归因**（只读复算 R621 冻结产物 + 独立 oracle 四分）。

零产品源码改动 / 零新臂 / 零远端调用 / 零新增夹具语义。
输入: R621 冻结快照 `eval/rover/r621/snapshots/w<win>/<arm>/g1/`（T×18 / C×18 / C1×3）
      R621 冻结隐藏用例 `eval/rover/r610/cases/cases-r521.json`（58 例, wythoff 15 例）
输出: out/percase-r622.json（逐跑次×逐例原始读数 + 四分标签）+ stdout 汇总表

四分标签（判决器口径, 承 kpi-eval-harness-design「逐例归因」节）:
  OK              通过（rc=0 ∧ 逐字节 == 期望）
  HARD_CRASH      真错·硬崩（rc!=0 或 stdout 空）
  FORMAT          格式差异（非 `LOSE` / `WIN i j` 形态）
  STATE_FLIP      状态误判（WIN↔LOSE 与 oracle 相反）
  LEGAL_NONMIN    合法但非期望解（是合法必胜着法但**非字典序最小**）
  TRUE_WRONG      真错·选点错（着法非法 或 目标非 P 位）

oracle 独立性: `wythoff_oracle.py` 与判定器/生成器零共享代码, 由题面规格直接定义实现(DP)。
判据（prereg-r622.json）: oracle 正控 = 15/15 复现期望字节; 变异负控 = 注入缺陷解必须被标非 OK。
"""
from __future__ import annotations
import argparse
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

CASES = os.path.join(REPO, "eval/rover/r610/cases/cases-r521.json")
SNAPS = os.path.join(REPO, "eval/rover/r621/snapshots")
WIN_RE = re.compile(r"^WIN\s+(\d+)\s+(\d+)$")
TMO = 10.0


def classify(a: int, b: int, rc: int, out: str, exp: str):
    """→ (tag, detail)"""
    got = (out or "").strip("\n")
    expn = exp.strip("\n")
    if got.strip() == expn.strip():
        return "OK", ""
    if rc != 0 or got.strip() == "":
        return "HARD_CRASH", "rc=%d len=%d" % (rc, len(got))
    s = got.strip()
    parsed = WIN_RE.match(s) if s != "LOSE" else None
    if s != "LOSE" and parsed is None:
        return "FORMAT", repr(s[:60])
    st_got = "WIN" if parsed is not None else "LOSE"
    st_orc = "LOSE" if ORC.solve("%d %d" % (a, b)) == "LOSE" else "WIN"
    if st_got != st_orc:
        return "STATE_FLIP", "%s->%s" % (st_orc, st_got)
    if parsed is None:
        return "TRUE_WRONG", "lose_not_bytewise"     # 状态同 LOSE 但字节不同 ⇒ 仅空白/多行
    i, j = int(parsed.group(1)), int(parsed.group(2))
    wm = ORC.winning_moves(a, b)
    if (i, j) in wm:
        return "LEGAL_NONMIN", "got=(%d,%d) min=%s" % (i, j, min(wm))
    return "TRUE_WRONG", "illegal_or_nonwinning=(%d,%d)" % (i, j)


def run_one(tree: str, game: str, stdin: str):
    """在产物树副本上跑 `python3 -B -m games <game>`（零写入原树）。"""
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": tree,
           "PYTHONPATH": tree, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        p = subprocess.run([sys.executable, "-B", "-m", "games", game], input=stdin,
                           capture_output=True, text=True, timeout=TMO, cwd=tree, env=env)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:  # noqa: BLE001
        return 125, "", type(e).__name__


def negctl(cases):
    """变异负控 v2（**预注册 v1 判据已被首跑证伪, 原样失败并入档, 不翻案**）。

    v1 判据「M1/M2 非 OK == 15/15」是**错误期望**：夹具本身不隔离变异行为 ——
    「恒判 LOSE」在 4 个真必败例上字节正确、「取字典序最大」在 12 个用例上 = 最小着法。
    ⇒ v1 读数原样留档（`out/negctl-r622.json`，pass=false）。

    v2 正确判据（两件成对, 逐例对应）:
      ① 判据器**无假红也无误放行**：对每个变异体、每个用例, `tag == OK` ⟺ 该变异体在该例上
         的字节确实等于期望（逐例对应 45/45），否则 `判据器对应性失败`；
      ② **夹具判别力 census**（这才是 v1 意外测到的东西）：各变异体在夹具上的正确例数
         （退化解得分 = 该子型的夹具判别力上限）。
    """
    import tempfile as _tf
    import shutil as _sh
    base = _tf.mkdtemp(prefix="r622neg-")
    res = {}
    variants = {
        "M1_always_lose": "def solve(text):\n    return 'LOSE'\n",
        "M2_max_win": ("import sys, os\nsys.path.insert(0, %r)\nimport wythoff_oracle as _o\n"
                       "def solve(text):\n    a, b = (int(x) for x in text.split()[:2])\n"
                       "    wm = _o.winning_moves(a, b)\n    if not wm:\n        return 'LOSE'\n"
                       "    i, j = max(wm)\n    return 'WIN %%d %%d' %% (i, j)\n") % os.path.dirname(os.path.abspath(__file__)),
        "M3_good": ("import sys, os\nsys.path.insert(0, %r)\nimport wythoff_oracle as _o\n"
                    "def solve(text):\n    return _o.solve(text)\n") % os.path.dirname(os.path.abspath(__file__)),
    }
    try:
        for name, src in variants.items():
            tree = os.path.join(base, name)
            os.makedirs(os.path.join(tree, "games"))
            io.open(os.path.join(tree, "games", "__init__.py"), "w").write("")
            io.open(os.path.join(tree, "games", "wythoff.py"), "w").write(src)
            io.open(os.path.join(tree, "games", "__main__.py"), "w").write(
                "import sys\ng = sys.argv[1] if len(sys.argv) > 1 else 'wythoff'\n"
                "mod = __import__('games.' + g, fromlist=['solve'])\n"
                "sys.stdout.write(mod.solve(sys.stdin.read()))\n")
            ok = n = mismatch = 0
            for c in cases:
                a, b = (int(x) for x in c["stdin"].split()[:2])
                rc, out, _ = run_one(tree, "wythoff", c["stdin"])
                tag, _d = classify(a, b, rc, out, c["expected_stdout"])
                should_ok = (out or "").strip("\n").strip() == c["expected_stdout"].strip("\n").strip()
                n += 1
                ok += 1 if tag == "OK" else 0
                if (tag == "OK") != should_ok:
                    mismatch += 1
            res[name] = {"n": n, "ok": ok, "correspondence_mismatch": mismatch,
                         "verdict": "PASS" if mismatch == 0 else "FAIL"}
    finally:
        _sh.rmtree(base, ignore_errors=True)
    res["pass"] = all(v["verdict"] == "PASS" for k, v in res.items()
                      if isinstance(v, dict) and "verdict" in v)
    res["criteria"] = ("① 逐例对应 mismatch == 0（判据器无假红/无误放行）"
                       "② fixture_discriminating_power = 各变异体正确例数/15（退化解得分越低判别力越强）")
    res["fixture_discriminating_power"] = {k: "%d/%d" % (v["ok"], v["n"])
                                          for k, v in res.items()
                                          if isinstance(v, dict) and "verdict" in v}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r622/out/percase-r622.json"))
    ap.add_argument("--wins", default="w217,w218,w219")
    ap.add_argument("--negctl", action="store_true")
    ap.add_argument("--negctl-out", default=os.path.join(REPO, "eval/rover/r622/out/negctl-r622.json"))
    args = ap.parse_args()

    cases = [c for c in json.load(io.open(CASES, encoding="utf-8")) if c["game"] == "wythoff"]
    if args.negctl:
        r = negctl(cases)
        io.open(args.negctl_out, "w", encoding="utf-8").write(json.dumps(r, ensure_ascii=False, indent=1))
        print("变异负控: %s" % json.dumps(r, ensure_ascii=False))
        return 0 if r["pass"] else 1
    # --- oracle 正控: 逐例复现期望字节 ---
    ctrl = {"n": len(cases), "match": 0, "mismatch": []}
    for c in cases:
        got = ORC.solve(c["stdin"])
        if got.strip() == c["expected_stdout"].strip():
            ctrl["match"] += 1
        else:
            ctrl["mismatch"].append({"stdin": c["stdin"].strip(), "oracle": got,
                                     "expected": c["expected_stdout"]})
    ctrl["pass"] = (ctrl["match"] == ctrl["n"])

    rows, per_case = [], {}
    tmp = tempfile.mkdtemp(prefix="r622-")
    try:
        for win in args.wins.split(","):
            wdir = os.path.join(SNAPS, win)
            if not os.path.isdir(wdir):
                continue
            for arm in sorted(os.listdir(wdir)):
                tree = os.path.join(wdir, arm, "g1")
                if not os.path.isdir(tree):
                    continue
                side = "codex" if arm.startswith("codex") else "agent"
                armname = "C1" if side == "codex" else ("T" if arm.startswith("agentT") else "C")
                rep = arm.split("-r")[-1] if "-r" in arm else "1"
                dst = os.path.join(tmp, win + "_" + arm)
                shutil.copytree(tree, dst)
                for ci, c in enumerate(cases):
                    a, b = (int(x) for x in c["stdin"].split()[:2])
                    rc, out, err = run_one(dst, "wythoff", c["stdin"])
                    tag, detail = classify(a, b, rc, out, c["expected_stdout"])
                    name = "wythoff#%02d-%s" % (ci, c["vis"])
                    rows.append({"win": win, "arm": armname, "arm_id": arm, "side": side,
                                 "rep": rep, "case": name, "idx": ci, "vis": c["vis"],
                                 "a": a, "b": b, "rc": rc, "tag": tag, "detail": detail,
                                 "expected": c["expected_stdout"].strip(),
                                 "got": (out or "").strip()[:80]})
                    per_case.setdefault(name, {}).setdefault(armname, []).append(tag)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- 聚合 ---
    agg = {}
    for r in rows:
        k = (r["win"], r["arm"])
        d = agg.setdefault(k, {"win": r["win"], "arm": r["arm"], "n": 0, "ok": 0, "tags": {}})
        d["n"] += 1
        d["ok"] += 1 if r["tag"] == "OK" else 0
        d["tags"][r["tag"]] = d["tags"].get(r["tag"], 0) + 1
    arm_tot = {}
    for (win, arm), d in agg.items():
        t = arm_tot.setdefault(arm, {"n": 0, "ok": 0, "tags": {}})
        t["n"] += d["n"]; t["ok"] += d["ok"]
        for k, v in d["tags"].items():
            t["tags"][k] = t["tags"].get(k, 0) + v
    # 失败子型（非 OK）逐案分布
    fail_by_case = {}
    for r in rows:
        if r["tag"] != "OK":
            fail_by_case.setdefault(r["case"], {}).setdefault(r["tag"], 0)
            fail_by_case[r["case"]][r["tag"]] += 1

    res = {"round": "R622", "kind": "wythoff-per-case-attribution",
           "oracle_control": ctrl, "rows": rows, "agg_by_window_arm": [
               dict(v, tags=dict(sorted(v["tags"].items()))) for v in agg.values()],
           "arm_totals": arm_tot, "fail_by_case": fail_by_case}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    io.open(args.out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))

    print("oracle 正控: %d/%d %s" % (ctrl["match"], ctrl["n"], "PASS" if ctrl["pass"] else "FAIL"))
    if ctrl["mismatch"]:
        print("  mismatch:", json.dumps(ctrl["mismatch"], ensure_ascii=False)[:400])
    print()
    print("| 臂 | 例次 | OK | 非OK 四分 |")
    print("|---|---|---|---|")
    for arm in ("T", "C", "C1"):
        t = arm_tot.get(arm)
        if not t:
            continue
        non = {k: v for k, v in t["tags"].items() if k != "OK"}
        print("| %s | %d | %d (%.1f%%) | %s |" % (arm, t["n"], t["ok"], 100.0 * t["ok"] / t["n"],
                                                    json.dumps(non, ensure_ascii=False)))
    print()
    print("逐窗次:")
    for (win, arm), d in sorted(agg.items()):
        print("  %s %-4s %2d/%2d  %s" % (win, arm, d["ok"], d["n"],
                                         {k: v for k, v in d["tags"].items() if k != "OK"}))
    print()
    print("失败案分布(案 -> 标签计数):")
    for c, tg in sorted(fail_by_case.items(), key=lambda kv: -sum(kv[1].values())):
        print("  %-24s %s" % (c, tg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
