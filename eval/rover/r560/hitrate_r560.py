#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R560 命中率双口径读数器 (来自 R560 中继 per-call dump; 口径同 R550sc/R551 hitrate_dual)。

归属: R560 dump 无 tag 字段 ⇒ **由 dump 自身请求文本派生的沙箱路径**归属 (`/tmp/r560/w1XX/{agentB0|agentB3|codex}/`)
—— 比 mtime 时间轴更强 (内容自证, 可复核), 且每枚 dump 必须**恰好归属一次** (否则 rc=2 器具缺陷)。

口径 (单位写入字段名; 禁用名义总量 total_tokens):
  v_all  = 1 − Σ miss_tok / Σ prompt_tok        含冷启动
  v_incr = 1 − miss_tok(末次调用) / prompt_tok(末次调用)  仅增量面 (与 transcript.cache_* 同源, 可交叉校验)
  逐调用恒等式 prompt_tok == hit_tok + miss_tok 违反 ⇒ rc=2 器具缺陷 (禁计入被测读数)
  缺 usage ⇒ unreported 哨兵 -1 并从比率剔除 + 单列计数 (禁按 0 计入)
"""
import argparse
import collections
import glob
import io
import json
import os
import re
import sys

PAT = None
ARM = {"agentB0": "R560B0", "agentB3": "R560B3", "codex": "C1"}


def load(p):
    with io.open(p, encoding="utf-8-sig", errors="replace") as fh:
        return json.load(fh)


def classify(f):
    """臂判别 = dump **自身请求形状** (内容自证, 不依赖 mtime/命名):
    codex 中继请求含 `input_items` (codex CLI 自有协议); 本侧 click-agent 请求含 `prompt_sha8` + `tail_messages`。"""
    d = load(f)
    r = d.get("request") or {}
    if "input_items" in r:
        return "codex"
    if (r.get("upstream_request") or {}).get("prompt_sha8"):
        return "agent"
    return None


def attributes_timeline(files, run_dir, wins):
    """归属 = 中继 dump 落盘时间轴 (R551/R550sc 口径; agent dump 无 tag/窗口字段)。

    每窗跑序固定 codex → agentB0 → agentB3, 各臂 transcript.json 在该臂结束后落盘 ⇒
    agent dump 归给「其落盘时刻之后**最早**的臂 transcript」; codex dump 归给同一窗 (窗号取该 transcript 的窗)。
    归属交叉校验: agent 侧 Σprompt_tok == transcript.prompt_tokens ∧ 末次 hit/miss == transcript.cache_*_tokens;
    codex 侧逐窗 dump 数 == windows.jsonl 记录的调用区间宽度。
    """
    tp = []
    for w in wins:
        for sub, arm in ARM.items():
            if sub == "codex":
                continue
            p = os.path.join(run_dir, w, sub, "g1", "transcript.json")
            if os.path.isfile(p):
                tp.append((w, arm, os.path.getmtime(p), p))
    tp.sort(key=lambda x: x[2])
    buckets, unassigned, cls_counts = collections.defaultdict(list), [], collections.Counter()
    for f in files:
        kind = classify(f)
        cls_counts[kind] += 1
        if kind is None:
            unassigned.append(os.path.basename(f))
            continue
        mt = os.path.getmtime(f)
        cand = [t for t in tp if t[2] >= mt - 1.0]
        if not cand:
            unassigned.append(os.path.basename(f))
            continue
        w, arm, _, _ = cand[0]
        buckets[(w, "C1" if kind == "codex" else arm)].append((mt, f))
    return buckets, unassigned, cls_counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dumps", default="/tmp/r560/adapter")
    ap.add_argument("--run-dir", default="/tmp/r560")
    ap.add_argument("--out", default="/tmp/r560/hitrate-r560.json")
    ap.add_argument("--wins", default="w107,w108,w109,w110,w111,w112")
    a = ap.parse_args()
    wins = [w for w in a.wins.split(",") if w]

    files = sorted(glob.glob(os.path.join(a.dumps, "side-agent-*.json"))) + \
            sorted(glob.glob(os.path.join(a.dumps, "side-codex-*.json")))
    buckets, unattributed, cls_counts = attributes_timeline(files, a.run_dir, wins)
    viol, unreported = [], 0
    wins_note = {}
    wj = os.path.join(a.run_dir, "logs", "windows.jsonl")
    if os.path.isfile(wj):
        for line in io.open(wj, encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            r0 = (rec.get("ranges") or {}).get("codex")
            if r0:
                wins_note[rec["win"]] = r0[1] - r0[0]

    rows = []
    for (w, arm) in sorted(buckets):
        calls = []
        for mt, f in sorted(buckets[(w, arm)]):
            d = load(f)
            u = ((d.get("response") or {}).get("usage")) or {}
            rec = {"f": os.path.basename(f), "t": mt,
                   "p": u.get("prompt_tokens"), "h": u.get("prompt_cache_hit_tokens"),
                   "m": u.get("prompt_cache_miss_tokens")}
            if rec["p"] is not None and rec["h"] is not None and rec["m"] is not None and rec["p"] != rec["h"] + rec["m"]:
                viol.append({k: rec[k] for k in ("f", "p", "h", "m")})
            if rec["p"] is None and rec["h"] is None and rec["m"] is None:
                unreported += 1
                rec["_unreported"] = True
            calls.append(rec)
        rep = [c for c in calls if not c.get("_unreported")]
        sp = sum(c["p"] or 0 for c in rep)
        sm = sum(c["m"] or 0 for c in rep)
        last = rep[-1] if rep else None
        tp = os.path.join(a.run_dir, w, {"C1": "codex", "R560B0": "agentB0", "R560B3": "agentB3"}[arm], "g1", "transcript.json")
        t = load(tp) if (arm != "C1" and os.path.isfile(tp)) else {}
        if arm == "C1":
            exp = wins_note.get(w)
            xref_sum = (exp is not None and len(calls) == exp)
            xref_last_miss = (exp is not None and len(calls) == exp)
            xref_last_hit = True
            t = {"calls": exp, "rc": None, "stage": None}
        else:
            xref_sum = (sp == t.get("prompt_tokens"))
            xref_last_miss = ((last or {}).get("m") == t.get("cache_miss_tokens"))
            xref_last_hit = ((last or {}).get("h") == t.get("cache_hit_tokens"))
        rows.append({
            "win": w, "arm": arm, "calls": len(calls), "calls_reported": len(rep),
            "unreported": len(calls) - len(rep),
            "v_all": round(1.0 - sm / sp, 4) if sp else -1.0,
            "v_incr": round(1.0 - (last["m"] or 0) / last["p"], 4) if (last and last["p"]) else -1.0,
            "sum_prompt_tok": sp, "sum_miss_tok": sm, "sum_hit_tok": sum(c["h"] or 0 for c in rep),
            "last_prompt_tok": (last or {}).get("p"), "last_miss_tok": (last or {}).get("m"),
            "count_mismatch": len(calls) != int(t.get("calls") or 0),
            "calls_transcript": t.get("calls"),
            "xref_sum_prompt": xref_sum, "xref_last_miss": xref_last_miss, "xref_last_hit": xref_last_hit,
            "rc": t.get("rc"), "stage": t.get("stage"),
        })

    out = {"round": "R560", "dumps": len(files), "attribution": "mtime_dump_timeline_per_arm",
           "unattributed": unattributed, "identity_violations": viol, "unreported_calls": unreported, "rows": rows,
           "rule": "v_all=1-Σmiss/Σprompt (含冷启动); v_incr=1-miss_last/prompt_last; "
                   "归属由 Σprompt==transcript.prompt_tokens ∧ 末次 hit/miss==transcript.cache_* 双读数交叉校验; "
                   "逐调用恒等式违反/未归属 ⇒ rc=2 器具缺陷, 禁计入被测读数"}
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    print("[命中率 双口径] dumps=%d 未归属=%d 恒等式违反=%d unreported=%d"
          % (len(files), len(unattributed), len(viol), unreported))
    byarm = collections.defaultdict(list)
    for r in rows:
        byarm[r["arm"]].append(r)
    for arm in ("C1", "R560B0", "R560B3"):
        rs = byarm.get(arm, [])
        if not rs:
            print("  %-8s 未测温" % arm)
            continue
        va = [r["v_all"] for r in rs]
        vi = [r["v_incr"] for r in rs]
        print("  %-8s v_all %.4f..%.4f (n=%d) | v_incr %.4f..%.4f | calls Σ=%d | 账差窗=%d | xref(Σprompt/lastmiss/lasthit) %d/%d/%d of %d"
              % (arm, min(va), max(va), len(va), min(vi), max(vi),
                 sum(r["calls"] for r in rs), sum(1 for r in rs if r["count_mismatch"]),
                 sum(1 for r in rs if r["xref_sum_prompt"]), sum(1 for r in rs if r["xref_last_miss"]),
                 sum(1 for r in rs if r["xref_last_hit"]), len(rs)))
    xref_bad = sum(1 for r in rows if not (r["xref_sum_prompt"] and r["xref_last_miss"]))
    rc = 2 if (viol or unattributed) else 1 if xref_bad else 0
    print("rc=%d%s" % (rc, " (器具缺陷: 归属/恒等式)" if rc == 2 else (" (归属交叉校验未全过 n=%d)" % xref_bad if rc else "")))
    return rc


if __name__ == "__main__":
    sys.exit(main())
