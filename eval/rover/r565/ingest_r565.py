#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R565 汇总器: 四侧读数从**同一** adapter dump 按索引区段归属 (禁跨轮相减; 口径同 R554/R555/R557)。

本轮差异 (逐条声明):
  · 臂 = C1 (codex 外部真值) + R565B0 (MAX_EXEC_REPAIR=0) （产品默认档; 剂量轴按 R561 收口不再复跑）。
    **同一枚二进制** (R556 交付件 sha 320d0eb1…), 单变量 = 唯一 env 开关 ⇒ 同窗四臂配对对照;
  · 调用/命中口径 = 中继 dump 索引区段 (R555 已证 transcript.calls 会漏掉续写调用);
  · 主判据读数 = cases_pass + transcript.exec_repairs/public_probe_* (剂量是否被行使) + rc/stage。
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


TR_FIELDS = ("calls", "max_exec_repair", "prompt_tokens", "completion_tokens", "cache_hit_tokens", "cache_miss_tokens",
             "rc", "stage", "reason", "plan_steps_total", "steps_executed", "exec_repairs",
             "repair_rounds", "prefix_chars", "self_test_unmet", "correctness_asserted",
             "public_probe_ran", "public_probe_reason", "public_probe_total", "public_probe_failed",
             "public_probe_trigger_rc")


def transcript(path):
    if not os.path.isfile(path):
        return {}
    try:
        t = json.load(io.open(path, encoding="utf-8"))
        return {k: t.get(k) for k in TR_FIELDS}
    except Exception as e:
        return {"err": str(e)[:80]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", required=True)
    ap.add_argument("--W", required=True)
    ap.add_argument("--pd", required=True)
    ap.add_argument("--codex-range", default="0,0")
    ap.add_argument("--b0-range", default="0,0")
    a = ap.parse_args()
    rng = lambda s: tuple(int(x) for x in s.split(","))
    adir = os.path.join(a.D, "adapter")
    nf = lambda p: sum(len(f) for _, _, f in os.walk(p)) if os.path.isdir(p) else 0
    empty = {"calls": 0, "prompt": 0, "new_prompt": 0, "hit": 0, "completion": 0,
             "turns": [], "v_all": None, "v_incr": None, "dump_files": [], "bad_dumps": []}

    spec = [("C1", "codex", "codex", rng(a.codex_range)),
            ("R565B0", "agent", "agentB0", rng(a.b0_range)),
]
    rec = {"round": "R565", "win": a.W, "arms": {}}
    rows, arms_art = [], {}
    for arm, side, sub, r in spec:
        st = arm_stats(adir, side, r) if r[1] > r[0] else dict(empty)
        cases = parse_cases(os.path.join(a.D, a.W, sub, "g1", "cases.txt")) if st["calls"] else \
            {"total": 0, "pass": 0, "fails": [], "present": False}
        work = os.path.join(a.D, a.W, sub, "g1", "work")
        entry = {**st, "cases_pass": cases["pass"], "cases_total": cases["total"],
                 "all_pass": bool(cases["total"] == 58 and cases["pass"] == 58),
                 "failed_cases": cases["fails"], "work_files": nf(work), "side": side}
        entry["self_transcript"] = transcript(os.path.join(a.D, a.W, sub, "g1", "transcript.json")) \
            if side == "agent" else {}
        rec["arms"][arm] = entry
        if st["calls"]:
            tr = entry["self_transcript"]
            rows.append({"arm": arm, "tid": "g1", "side": side, "all_pass": entry["all_pass"],
                         "cases_pass": cases["pass"], "cases_total": cases["total"],
                         "calls": st["calls"], "new_prompt": st["new_prompt"], "prompt": st["prompt"],
                         "completion": st["completion"], "v_all": st["v_all"], "v_incr": st["v_incr"],
                         "rc": tr.get("rc"), "stage": tr.get("stage"),
                         "exec_repairs": tr.get("exec_repairs"),
                         "public_probe_failed": tr.get("public_probe_failed"),
                         "public_probe_ran": tr.get("public_probe_ran"),
                         "self_test_unmet": tr.get("self_test_unmet")})
            arms_art[arm] = {"side": side, "dir": "%s/g1" % sub, "work_files": nf(work),
                             "cases": cases["total"],
                             "contract_death": bool(tr.get("stage") == "contract"),
                             "exec_repairs": tr.get("exec_repairs"),
                             "public_probe_ran": tr.get("public_probe_ran"),
                             "public_probe_failed": tr.get("public_probe_failed")}
    rec["ledger_check"] = {k: {"dump_calls": v["calls"], "transcript_calls": v["self_transcript"].get("calls"),
                               "diff": (v["self_transcript"].get("calls") or 0) - v["calls"]}
                           for k, v in rec["arms"].items() if k.startswith("R565") and v["calls"]}
    rec["rule"] = "调用/新算 prompt 取中继 dump 索引区段; 剂量行使 ⇔ transcript.exec_repairs>0; 账核对 = dump 区段 vs transcript.calls"
    with io.open(os.path.join(a.D, a.W, "readings.json"), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
    with io.open(os.path.join(a.D, "readings-r565.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    wdir = os.path.join(a.pd, "evidence", "windows", a.W)
    os.makedirs(wdir, exist_ok=True)
    json.dump({"round": "R565", "win": a.W, "rows": rows},
              io.open(os.path.join(wdir, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"win": a.W, "arms": arms_art,
               "note": "快照 = snapshots/<win>/{C1,agentB0}/g1/**; 判分脚本 cases/run_cases_r521.py"},
              io.open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    desc = "  [R565 %s]" % a.W
    for arm in ("C1", "R565B0"):
        v = rec["arms"][arm]
        if v["calls"]:
            desc += " %s=%d/%d calls=%d new=%d rc=%s stage=%s xrep=%s" % (
                arm, v["cases_pass"], v["cases_total"], v["calls"], v["new_prompt"],
                v["self_transcript"].get("rc"), v["self_transcript"].get("stage"),
                v["self_transcript"].get("exec_repairs"))
    print(desc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
