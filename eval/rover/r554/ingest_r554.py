#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R554 汇总器: 把两侧(同窗)读数从**同一** adapter dump 时间轴按臂索引区段归属, 并落证据面。

口径 (与 R553 同源, 禁跨轮相减):
  · calls      = 该臂在该窗内的 dump 条数 (side-codex-NNN / side-agent-NNN 索引区段, 由 runner 逐臂截取)
  · prompt     = Σ usage.prompt_tokens      (全部调用)
  · new_prompt = Σ usage.prompt_cache_miss_tokens   (新算 prompt; 缺键 ⇒ prompt-hit 回算)
  · hit        = Σ usage.prompt_cache_hit_tokens
  · v_all      = hit/prompt (含冷启动)      v_incr = 仅第 2..n 次调用的 hit/prompt (去冷启动)
  · 判分       = cases.txt (同一隐藏用例脚本对**该臂产物树**实跑), 不吃自报
输出: $D/$W/readings.json, $D/readings-r554.jsonl, <pd>/evidence/windows/<W>/{report.json,artifacts.json}
"""
from __future__ import annotations
import argparse, glob, io, json, os, re, sys


def _usage(u):
    if not u:
        return {}
    p = int(u.get("prompt_tokens") or 0)
    hit = u.get("prompt_cache_hit_tokens")
    miss = u.get("prompt_cache_miss_tokens")
    if hit is None:
        hit = ((u.get("prompt_tokens_details") or {}).get("cached_tokens"))
    if hit is None:
        hit = 0
    hit = int(hit)
    if miss is None:
        miss = max(p - hit, 0)
    return {"prompt": p, "hit": hit, "miss": int(miss),
            "completion": int(u.get("completion_tokens") or 0),
            "total": int(u.get("total_tokens") or (p + int(u.get("completion_tokens") or 0)))}


def arm_dumps(adapter_dir, side, rng):
    a, b = rng
    out = []
    for i in range(a + 1, b + 1):
        f = os.path.join(adapter_dir, "side-%s-%03d.json" % (side, i))
        if os.path.isfile(f):
            out.append(f)
    return out


def arm_stats(adapter_dir, side, rng):
    files = arm_dumps(adapter_dir, side, rng)
    agg = {"calls": len(files), "prompt": 0, "new_prompt": 0, "hit": 0, "completion": 0,
           "turns": [], "dump_files": [os.path.basename(f) for f in files]}
    for f in files:
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception as e:  # 坏 dump 不进读数, 但留痕
            agg.setdefault("bad_dumps", []).append({"file": os.path.basename(f), "err": str(e)[:60]})
            continue
        u = _usage(((d.get("response") or {}).get("usage")) or {})
        agg["prompt"] += u.get("prompt", 0)
        agg["hit"] += u.get("hit", 0)
        agg["new_prompt"] += u.get("miss", 0)
        agg["completion"] += u.get("completion", 0)
        agg["turns"].append({"file": os.path.basename(f), **u})
    n = agg["calls"]
    t = agg["turns"]
    agg["v_all"] = round(agg["hit"] / agg["prompt"], 4) if agg["prompt"] else None
    inc = t[1:]
    ip = sum(x["prompt"] for x in inc)
    agg["v_incr"] = round(sum(x["hit"] for x in inc) / ip, 4) if ip else None
    agg["v_incr_note"] = "去冷启动(仅第2..n次调用), n=%d" % len(inc)
    agg["expected_calls_hint"] = n
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
    return {"total": tot, "pass": pas, "fails": fails, "present": True,
            "tail": (L[-1] if L else "")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", required=True)
    ap.add_argument("--W", required=True)
    ap.add_argument("--pd", required=True)
    ap.add_argument("--tag", default="R554")
    ap.add_argument("--codex-range", required=True, help="n0,n1")
    ap.add_argument("--agent-range", required=True, help="n0,n1")
    a = ap.parse_args()
    cr = tuple(int(x) for x in a.codex_range.split(","))
    ar = tuple(int(x) for x in a.agent_range.split(","))

    codex = arm_stats(os.path.join(a.D, "adapter"), "codex", cr)
    agent = arm_stats(os.path.join(a.D, "adapter"), "agent", ar)
    jc = parse_cases(os.path.join(a.D, a.W, "codex", "g1", "cases.txt"))
    ja = parse_cases(os.path.join(a.D, a.W, "agent", "g1", "cases.txt"))

    # 自报交叉核对 (本侧 transcript; 只作对照, 不吃)
    tp = os.path.join(a.D, a.W, "agent", "g1", "transcript.json")
    self_rep = {}
    if os.path.isfile(tp):
        try:
            t = json.load(io.open(tp, encoding="utf-8"))
            self_rep = {k: t.get(k) for k in ("calls", "prompt_tokens", "completion_tokens",
                                              "cache_hit_tokens", "cache_miss_tokens", "rc", "stage")}
        except Exception as e:
            self_rep = {"err": str(e)[:80]}
    awork = os.path.join(a.D, a.W, "agent", "g1", "work")
    cwork = os.path.join(a.D, a.W, "codex", "g1", "work")
    nf = lambda p: sum(len(f) for _, _, f in os.walk(p)) if os.path.isdir(p) else 0
    rec = {"round": "R554", "win": a.W, "tag": a.tag,
           "codex": {**codex, "cases_pass": jc["pass"], "cases_total": jc["total"],
                     "all_pass": bool(jc["total"] == 58 and jc["pass"] == 58), "cases_tail": jc["tail"],
                     "failed_cases": jc["fails"], "work_files": nf(cwork), "side": "codex"},
           "agent": {**agent, "cases_pass": ja["pass"], "cases_total": ja["total"],
                     "all_pass": bool(ja["total"] == 58 and ja["pass"] == 58), "cases_tail": ja["tail"],
                     "failed_cases": ja["fails"], "work_files": nf(awork), "side": "agent",
                     "self_transcript": self_rep},
           "void": {"codex": bool(nf(cwork) == 0 or jc["total"] == 0),
                    "agent": bool(nf(awork) == 0 or ja["total"] == 0)},
           "rule": "VOID ⇔ 无产物(work_files==0) ∨ 无用例可判分(cases.total==0) (R553 新判据, 不用 rc/退化率)"}
    with io.open(os.path.join(a.D, a.W, "readings.json"), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
    with io.open(os.path.join(a.D, "readings-r554.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # --- 证据面 (前置器 project 布局) ---------------------------------------
    wdir = os.path.join(a.pd, "evidence", "windows", a.W)
    os.makedirs(wdir, exist_ok=True)
    rep = {"round": "R554", "win": a.W, "rows": [
        {"arm": a.tag, "tid": "g1", "side": "agent", "all_pass": rec["agent"]["all_pass"],
         "cases_pass": ja["pass"], "cases_total": ja["total"], "calls": agent["calls"],
         "new_prompt": agent["new_prompt"], "v_all": agent["v_all"]},
        {"arm": "C1", "tid": "g1", "side": "codex", "all_pass": rec["codex"]["all_pass"],
         "cases_pass": jc["pass"], "cases_total": jc["total"], "calls": codex["calls"],
         "new_prompt": codex["new_prompt"], "v_all": codex["v_all"]}]}
    json.dump(rep, io.open(os.path.join(wdir, "report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    arts = {"win": a.W, "arms": {
        "codex": {"side": "codex", "dir": "codex/g1", "work_files": nf(cwork), "cases": jc["total"]},
        "agent" + a.tag: {"side": "agent", "dir": "agent/g1", "work_files": nf(awork), "cases": ja["total"]}},
        "note": "两侧产物树快照 = snapshots/<win>/{codex,agent%s}/g1/**; 判分脚本 cases/run_cases_r521.py" % a.tag}
    json.dump(arts, io.open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("  [R554 %s] codex %d/%d calls=%d new=%d | %s %d/%d calls=%d new=%d" % (
        a.W, jc["pass"], jc["total"], codex["calls"], codex["new_prompt"],
        a.tag, ja["pass"], ja["total"], agent["calls"], agent["new_prompt"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
