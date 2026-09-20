#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R603 只读机检器（**零产品源码改动 / 零远端调用 / 只读在盘树**）。

三个读数面（承 skill `kpi-eval-harness-design` 的器具纪律；判词落**机读字段**，不活在散文里）：

  L2 `prefix_invariance` —— 前缀连续性机检（文献 L2 机制假设的机检断言显式化）：
      同一轮内所有跑次的 `prefix_chars` / `prefix_sha256` 必须**唯一**（恒前缀），
      `task_sha256` 必须唯一（同输入）。三件各给 distinct 计数 + 值。
  L3 `judgment_hygiene` —— 判定卫生 census（文献 L3「同源 oracle 假信心」）：
      逐跑次的失败判定来源必须来自**产物之外**（题面公开用例探针 / 外部用例套件 cases-r521）；
      统计「只有产物自证」的跑次数（目标 0）。
  Q1 `false_confidence` —— **假信心率**（机械口径，禁文本启发式）：
      `transcript.rc == 0`（链路自判达成）∧ 外部用例套件实得 **< 满分** ⇒ 链路自判与外部真值冲突。
      反向（rc≠0 ∧ 外部满分）同列，两侧都要报（成对）。
  附 `overclaim_heuristic`（**启发式，不入 rc、不进对外口径**）：回复正文含成功词 ∧ 外部未满分。

rc 语义（三分层，fail-closed）：0 全过 / 2 器具缺陷或读数异常 / 3 输入缺失（弃权）。
用法: python3 checks_r603.py --D <run根> [--pd eval/rover/r603] [--negctl]
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
HARNESS = os.path.expanduser("~/.agentframework/harness/runs")
TEXT_HEUR = re.compile(r"(全部通过|已通过|全部正确|全部用例通过|tests?\s+pass|all\s+pass|PASS\b)", re.I)


def read_transcript(p):
    try:
        d = json.load(io.open(p, encoding="utf-8", errors="replace"))
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def cases_result(p):
    """外部用例套件落盘形态: `R521_CASES <pass>/<total>` 尾行（外部真值，非产物自产）。"""
    try:
        txt = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return None
    m = None
    for m2 in re.finditer(r"R521_CASES\s+(\d+)\s*/\s*(\d+)", txt):
        m = m2
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def enumerate_runs(D):
    """跑次 = 目录（外部真值：磁盘目录数，不采信进程内 turn 计数）。"""
    out = []
    if not os.path.isdir(D):
        return out
    for win in sorted(os.listdir(D)):
        if not re.fullmatch(r"w\d+", win):
            continue
        for sub in sorted(os.listdir(os.path.join(D, win))):
            g1 = os.path.join(D, win, sub, "g1")
            if not os.path.isdir(g1):
                continue
            t = read_transcript(os.path.join(g1, "transcript.json"))
            c = cases_result(os.path.join(g1, "cases.txt"))
            arm = "codex" if sub == "codex" else ("T" if "agentDT" in sub else ("C" if "agentDC" in sub else sub))
            out.append({"win": win, "sub": sub, "arm": arm, "g1": g1, "t": t, "cases": c})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", default=os.path.join(HARNESS, "r603"))
    ap.add_argument("--pd", default=os.path.join(REPO, "eval/rover/r603"))
    ap.add_argument("--negctl", action="store_true", help="负控: 在副本上注入前缀漂移，器具必须报红")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    D = a.D
    runs = enumerate_runs(D)
    if a.negctl:
        # 负控（有牙证明）：把某一跑次的前缀 sha 改掉 ⇒ L2 必须报违反
        tmp = tempfile.mkdtemp(prefix="r603neg-")
        shutil.copytree(D, os.path.join(tmp, "r603"), symlinks=True,
                        ignore=shutil.ignore_patterns("work", "*.bin"))
        D = os.path.join(tmp, "r603")
        runs = enumerate_runs(D)
        ag = [r for r in runs if r["arm"] in ("T", "C") and r["t"]]
        if not ag:
            print(json.dumps({"rc": 3, "note": "负控无靶（无 agent 跑次）"}, ensure_ascii=False))
            return 3
        p = os.path.join(ag[0]["g1"], "transcript.json")
        d = read_transcript(p)
        if not isinstance(d, dict):
            print(json.dumps({"rc": 3, "note": "负控无靶（transcript 不可解析）"}, ensure_ascii=False))
            return 3
        d["prefix_sha256"] = "deadbeef" + (d.get("prefix_sha256") or "")[8:]
        json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False)
        runs = enumerate_runs(D)   # 器具自捕修复: 注入后必须**重枚举**（否则读的是注入前的内存副本 ⇒ 负控恒绿）
        print(json.dumps({"negctl_injected": {"run": ag[0]["win"] + "/" + ag[0]["sub"],
                                              "field": "prefix_sha256"}}, ensure_ascii=False))

    agent = [r for r in runs if r["arm"] in ("T", "C")]
    if not agent:
        res = {"rc": 3, "note": "输入缺失：无 agent 跑次 ⇒ 弃权（不判红）", "D": D}
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 3

    # --- L2 前缀不变 ---
    pc = sorted({r["t"]["prefix_chars"] for r in agent if r["t"] and "prefix_chars" in r["t"]})
    ps = sorted({r["t"]["prefix_sha256"] for r in agent if r["t"] and r["t"].get("prefix_sha256")})
    tsk = sorted({r["t"]["task_sha256"] for r in agent if r["t"] and r["t"].get("task_sha256")})
    missing = [r["win"] + "/" + r["sub"] for r in agent if not r["t"]]
    l2_ok = (len(pc) == 1 and len(ps) == 1 and len(tsk) == 1 and not missing)
    l2 = {"pass": bool(l2_ok), "prefix_chars_distinct": len(pc), "prefix_chars_values": pc,
          "prefix_sha256_distinct": len(ps), "prefix_sha256_values": [s[:16] + "…" for s in ps],
          "task_sha256_distinct": len(tsk), "task_sha256_values": [s[:16] + "…" for s in tsk],
          "transcript_missing": missing,
          "assertion": "同轮内 prefix_chars ∧ prefix_sha256 ∧ task_sha256 各唯一（恒前缀 + 同输入）"}

    # --- L3 判定卫生 census ---
    hy = {"runs_total": len(agent), "with_external_suite": 0, "with_public_probe": 0,
          "self_source_only": [], "neither": []}
    for r in agent:
        t = r["t"] or {}
        ext = r["cases"] is not None
        probe = int(t.get("public_probe_ran") or 0) > 0
        if ext:
            hy["with_external_suite"] += 1
        if probe:
            hy["with_public_probe"] += 1
        if not ext and not probe:
            hy["neither"].append(r["win"] + "/" + r["sub"])
        # 「自证」= 判定仅来自产物自带证据（题面公开用例 / 外部套件均缺席且仍判了失败）
        if not ext and not probe and int(t.get("rc") or 0) != 0:
            hy["self_source_only"].append(r["win"] + "/" + r["sub"])
    hy["pass"] = bool(not hy["self_source_only"])
    hy["assertion"] = "失败判定必须由产物之外给出（题面公开用例探针 ∧/∨ 外部用例套件）；self_source_only 目标 0"

    # --- Q1 假信心（机械） ---
    fc = {"rc0_but_external_unmet": [], "rc_non0_but_external_full": [], "skip_no_external": 0}
    for r in agent:
        t, c = r["t"] or {}, r["cases"]
        if c is None:
            fc["skip_no_external"] += 1
            continue
        pa, tot = c
        full = (tot > 0 and pa == tot)
        rc_raw = t.get("rc")
        rcv = -1 if rc_raw is None else int(rc_raw)   # 器具自捕修复: `0 or -1` ⇒ -1 (0 为假值) ⇒ rc==0 恒被判成 !=0, 假信心率**结构性恒 0**
        if rcv == 0 and not full:
            fc["rc0_but_external_unmet"].append({"run": r["win"] + "/" + r["sub"], "cases": "%d/%d" % (pa, tot),
                                                 "public_probe_failed": t.get("public_probe_failed"),
                                                 "artifact_carryover_rounds": t.get("artifact_carryover_rounds")})
        if rcv != 0 and full:
            fc["rc_non0_but_external_full"].append({"run": r["win"] + "/" + r["sub"], "rc": t.get("rc")})
    n_ext = len(agent) - fc["skip_no_external"]
    fc["rate"] = (round(len(fc["rc0_but_external_unmet"]) / n_ext, 4) if n_ext else None)
    fc["denominator"] = n_ext
    fc["assertion"] = "rc==0（链路自判达成）∧ 外部用例 < 满分 ⇒ 自判与外部真值冲突；反向同列"

    # --- 附: overclaim 启发式（不入 rc） ---
    oc = {"hits": [], "note": "文本形状启发式 —— 仅参考，不作对外口径、不入 rc"}
    for r in agent:
        c = r["cases"]
        if c is None:
            continue
        pa, tot = c
        if pa == tot:
            continue
        try:
            rp = io.open(os.path.join(r["g1"], "reply.txt"), encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if TEXT_HEUR.search(rp):
            oc["hits"].append(r["win"] + "/" + r["sub"])

    drifts = [l2["prefix_chars_distinct"] != 1, l2["prefix_sha256_distinct"] != 1, bool(missing)]
    rc = 0
    if not l2_ok or not hy["pass"]:
        rc = 2 if not a.negctl else 0   # 负控跑: 报红即为「有牙」⇒ rc=0
    res = {"round": "R603", "kind": "只读机检（L2 前缀不变 / L3 判定卫生 / 假信心率）",
           "negctl_teeth": bool(a.negctl and any(drifts)),
           "D": D, "instrument": {"driver_sha12": hashlib.sha256(io.open(__file__, "rb").read()).hexdigest()[:12]},
           "L2_prefix_invariance": l2, "L3_judgment_hygiene": hy,
           "Q1_false_confidence": fc, "overclaim_heuristic": oc,
           "rc": rc, "rc_semantics": "0 全过 / 2 器具或读数异常 / 3 输入缺失（弃权）",
           "negctl": bool(a.negctl), "l2_violated": any(drifts)}
    out = a.out or os.path.join(a.pd, "checks-r603.json")
    json.dump(res, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ("rc", "negctl", "negctl_teeth", "l2_violated")}, ensure_ascii=False))
    print(json.dumps({"L2": l2, "L3": {k: hy[k] for k in ("pass", "runs_total", "with_external_suite",
                                                          "self_source_only", "neither")},
                      "Q1": {"rate": fc["rate"], "den": fc["denominator"],
                             "conflicts": len(fc["rc0_but_external_unmet"])},
                      "overclaim_heuristic": len(oc["hits"])}, ensure_ascii=False, indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main())
