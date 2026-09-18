#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R557 汇总器: 三侧读数从**同一** adapter dump 按索引区段归属 (禁跨轮相减; 口径同 R554/R555)。

本轮差异 (逐条声明):
  · 臂 = C1 (codex 外部真值) + R557A0 (未修复: /tmp/pub_r555/agenthost, sha d2813218…) + R557A1 (修复件);
    同窗同题面同夹具 ⇒ 配对对照;
  · 调用/命中口径 = 中继 dump 索引区段 (R555 已证 transcript.calls 会漏掉续写调用);
  · 主判据读数 = transcript.stage=="contract" (契约面死亡率) + cases_pass。
"""
from __future__ import annotations
import argparse, io, json, os, sys


def _usage(u):
    if not u:
        return {}
    p = int(u.get("prompt_tokens") or 0)
    hit = u.get("prompt_cache_hit_tokens")
    if hit is None:
        hit = ((u.get("prompt_tokens_details") or {}).get("cached_tokens"))
    if hit is None:
        hit = 0
    hit = int(hit)
    miss = u.get("prompt_cache_miss_tokens")
    if miss is None:
        miss = max(p - hit, 0)
    return {"prompt": p, "hit": hit, "miss": int(miss),
            "completion": int(u.get("completion_tokens") or 0)}


def arm_stats(adapter_dir, side, rng):
    a, b = rng
    files = [os.path.join(adapter_dir, "side-%s-%03d.json" % (side, i)) for i in range(a + 1, b + 1)]
    files = [f for f in files if os.path.isfile(f)]
    agg = {"calls": len(files), "prompt": 0, "new_prompt": 0, "hit": 0, "completion": 0,
           "turns": [], "dump_files": [os.path.basename(f) for f in files], "bad_dumps": []}
    for f in files:
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception as e:
            agg["bad_dumps"].append({"file": os.path.basename(f), "err": str(e)[:60]})
            continue
        u = _usage(((d.get("response") or {}).get("usage")) or {})
        for k, kk in (("prompt", "prompt"), ("hit", "hit"), ("miss", "new_prompt"), ("completion", "completion")):
            agg[kk] += u.get(k, 0)
        agg["turns"].append({"file": os.path.basename(f), **u})
    t = agg["turns"]
    agg["v_all"] = round(agg["hit"] / agg["prompt"], 4) if agg["prompt"] else None
    inc = t[1:]
    ip = sum(x["prompt"] for x in inc)
    agg["v_incr"] = round(sum(x["hit"] for x in inc) / ip, 4) if ip else None
    agg["v_incr_note"] = "去冷启动(仅第2..n次调用), n=%d" % len(inc)
    return agg


def parse_cases(path):
    tot = pas = 0
    fails = []
    if not os.path.isfile(path):
        return {"total": 0, "pass": 0, "fails": [], "present": False}
    L = io.open(path, encoding="utf-8", errors="replace").read().splitlines()
    for x in L:
        if x.startswith("CASE"):
            tot += 1
            if "PASS" in x:
                pas += 1
            else:
                fails.append(x.split()[1])
    return {"total": tot, "pass": pas, "fails": fails, "present": True, "tail": (L[-1] if L else "")}


def transcript(path):
    if not os.path.isfile(path):
        return {}
    try:
        t = json.load(io.open(path, encoding="utf-8"))
        return {k: t.get(k) for k in ("calls", "prompt_tokens", "completion_tokens",
                                     "cache_hit_tokens", "cache_miss_tokens", "rc", "stage",
                                     "plan_steps_total", "exec_repairs", "probe_repairs",
                                     "prefix_chars", "self_test_unmet")}
    except Exception as e:
        return {"err": str(e)[:80]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", required=True)
    ap.add_argument("--W", required=True)
    ap.add_argument("--pd", required=True)
    ap.add_argument("--codex-range", default="0,0")
    ap.add_argument("--a0-range", default="0,0")
    ap.add_argument("--a1-range", required=True)
    a = ap.parse_args()
    rng = lambda s: tuple(int(x) for x in s.split(","))
    adir = os.path.join(a.D, "adapter")
    nf = lambda p: sum(len(f) for _, _, f in os.walk(p)) if os.path.isdir(p) else 0
    empty = {"calls": 0, "prompt": 0, "new_prompt": 0, "hit": 0, "completion": 0,
             "turns": [], "v_all": None, "v_incr": None, "dump_files": [], "bad_dumps": []}

    spec = [("C1", "codex", "codex", rng(a.codex_range)),
            ("R557A0", "agent", "agentA0", rng(a.a0_range)),
            ("R557A1", "agent", "agentA1", rng(a.a1_range))]
    rec = {"round": "R557", "win": a.W, "arms": {}}
    rows, arms_art = [], {}
    for arm, side, sub, r in spec:
        st = arm_stats(adir, side, r) if r[1] > r[0] else dict(empty)
        cases = parse_cases(os.path.join(a.D, a.W, sub, "g1", "cases.txt")) if st["calls"] else \
            {"total": 0, "pass": 0, "fails": [], "present": False}
        work = os.path.join(a.D, a.W, sub, "g1", "work")
        entry = {**st, "cases_pass": cases["pass"], "cases_total": cases["total"],
                 "all_pass": bool(cases["total"] == 58 and cases["pass"] == 58),
                 "failed_cases": cases["fails"], "work_files": nf(work), "side": side}
        if side == "agent":
            entry["self_transcript"] = transcript(os.path.join(a.D, a.W, sub, "g1", "transcript.json"))
        else:
            entry["self_transcript"] = {}
        rec["arms"][arm] = entry
        if st["calls"]:
            row = {"arm": arm, "tid": "g1", "side": side, "all_pass": entry["all_pass"],
                   "cases_pass": cases["pass"], "cases_total": cases["total"],
                   "calls": st["calls"], "new_prompt": st["new_prompt"], "prompt": st["prompt"],
                   "completion": st["completion"], "v_all": st["v_all"],
                   "rc": entry["self_transcript"].get("rc"),
                   "stage": entry["self_transcript"].get("stage")}
            rows.append(row)
            arms_art[arm] = {"side": side, "dir": "%s/g1" % sub, "work_files": nf(work),
                             "cases": cases["total"],
                             "contract_death": bool(entry["self_transcript"].get("stage") == "contract")}
    rec["contract_death"] = {k: bool(v["self_transcript"].get("stage") == "contract")
                             for k, v in rec["arms"].items() if k.startswith("R557")}
    rec["rule"] = "调用/新算 prompt 取中继 dump 索引区段; 契约面死亡 ⇔ transcript.stage=='contract' (R557 主判据)"
    with io.open(os.path.join(a.D, a.W, "readings.json"), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
    with io.open(os.path.join(a.D, "readings-r557.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    wdir = os.path.join(a.pd, "evidence", "windows", a.W)
    os.makedirs(wdir, exist_ok=True)
    json.dump({"round": "R557", "win": a.W, "rows": rows},
              io.open(os.path.join(wdir, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"win": a.W, "arms": arms_art,
               "note": "快照 = snapshots/<win>/{C1,agentR557A0,agentR557A1}/g1/**; 判分脚本 cases/run_cases_r521.py"},
              io.open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    desc = "  [R557 %s]" % a.W
    for arm in ("C1", "R557A0", "R557A1"):
        v = rec["arms"][arm]
        if v["calls"]:
            desc += " %s=%d/%d calls=%d new=%d rc=%s stage=%s" % (
                arm, v["cases_pass"], v["cases_total"], v["calls"], v["new_prompt"],
                v["self_transcript"].get("rc"), v["self_transcript"].get("stage"))
    print(desc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
