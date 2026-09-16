#!/usr/bin/env python3
"""R505 多批汇总（H7 质量面 n≥3 + 判据② 汇总 + 跨时间 H9 第二次读）。

判据（预注册, 先于首跑）:
  H7 = 3 批同窗; 逐题 mode 一致率 + 整题全对数; agent 一侧不得低于 codex 一侧（"质量不降"）。
  H8 = 逐题调用构成（每侧/每批 unmatched==0, ambiguous==0）+ 判据② 目标（本侧每轮调用数 ≤ 目标值, 目标记在 prereg）。
  H9 = 对每批仓内快照再跑一次 check_usage_replay（跨时间第二次读）全须 rc=0。
用法: python3 eval/rover/r505/agg_r505.py [--batches a b c] [--calls-target 14]
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PY = sys.executable


def load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", nargs="+", default=["a", "b", "c"])
    ap.add_argument("--calls-target", type=int, default=14)
    ap.add_argument("--out", default=os.path.join(HERE, "evidence", "agg-r505.json"))
    a = ap.parse_args()

    per_batch, rows = {}, []
    replay_fail = []
    for b in a.batches:
        ev = os.path.join(HERE, "evidence", b)
        vp = os.path.join(ev, "verdict-r505%s.json" % b)
        if not os.path.exists(vp):
            per_batch[b] = {"status": "missing", "verdict": vp}
            print("[告警] 批 %s 缺判据产物: %s" % (b, vp))
            continue
        v = load(vp)
        per_batch[b] = {"status": "ok", "rc": v.get("rc"), "table": v.get("table"),
                        "criteria": {c["id"]: bool(c.get("pass")) for c in v.get("criteria", [])},
                        "totals": v.get("totals"), "attribution": v.get("attribution")}
        for t in v.get("table") or []:
            rows.append({"batch": b, **t})
        for side in ("codex", "agent"):
            usage = os.path.join(ev, "adapter-%s" % side, "usage-%s.txt" % side)
            if not os.path.exists(usage):
                replay_fail.append({"batch": b, "side": side, "why": "缺冻结 usage 清单"})
                continue
            outp = os.path.join(ev, "replay-%s-%s-late.json" % (side, b))
            r = subprocess.run([PY, os.path.join(HERE, "check_usage_replay.py"),
                                "--usage", usage, "--dir", os.path.join(ev, "adapter-%s" % side),
                                "--out", outp], capture_output=True, text=True)
            if r.returncode != 0:
                replay_fail.append({"batch": b, "side": side, "rc": r.returncode,
                                    "tail": (r.stdout or "").strip().splitlines()[-3:]})

    tids = sorted({r["tid"] for r in rows})
    h7_rows, codex_ok_tot, agent_ok_tot, agree_tot, obs_tot = [], 0, 0, 0, 0
    for tid in tids:
        rs = [r for r in rows if r["tid"] == tid]
        c_ok = sum(1 for r in rs if r.get("codex_mode") == "ok")
        a_ok = sum(1 for r in rs if r.get("agent_mode") == "ok")
        agree = sum(1 for r in rs if r.get("codex_mode") == r.get("agent_mode") and r.get("codex_mode"))
        codex_ok_tot += c_ok
        agent_ok_tot += a_ok
        agree_tot += agree
        obs_tot += len(rs)
        h7_rows.append({"tid": tid, "family": rs[0].get("family"), "n_batches": len(rs),
                        "codex_ok": c_ok, "agent_ok": a_ok, "mode_agree": agree,
                        "codex_modes": [r.get("codex_mode") for r in rs],
                        "agent_modes": [r.get("agent_mode") for r in rs]})

    batch_rows = []
    for b in a.batches:
        s = per_batch.get(b) or {}
        if s.get("status") != "ok":
            batch_rows.append({"batch": b, "status": "missing"})
            continue
        t = s["totals"]
        cu, au = t["codex"]["usage"], t["agent"]["usage"]
        batch_rows.append({
            "batch": b, "rc": s["rc"],
            "codex": {"whole_ok": t["codex"]["whole_ok"], "n": t["codex"]["n"],
                      "calls": cu["calls"], "tok": cu["total_tokens"]},
            "agent": {"whole_ok": t["agent"]["whole_ok"], "n": t["agent"]["n"],
                      "calls": au["calls"], "tok": au["total_tokens"]},
            "agent_calls_by_task": {e["tid"]: e["calls"] for e in
                                    ((s["attribution"] or {}).get("agent") or {}).get("by_task", [])},
            "criteria_fail": [k for k, ok in (s["criteria"] or {}).items() if not ok],
        })

    a_calls = [r["agent"]["calls"] for r in batch_rows if r.get("agent")]
    c_calls = [r["codex"]["calls"] for r in batch_rows if r.get("codex")]
    h8_meta = []
    for b in a.batches:
        s = per_batch.get(b) or {}
        if s.get("status") != "ok":
            continue
        ag = (s["attribution"] or {}).get("agent") or {}
        h8_meta.append({"batch": b, "unmatched": len(ag.get("unmatched") or []),
                        "ambiguous": len(ag.get("ambiguous") or []),
                        "calls": ag.get("calls")})

    agg = {
        "round": "R505", "batches": a.batches,
        "per_batch": batch_rows,
        "H7": {"rows": h7_rows, "codex_ok_total": codex_ok_tot, "agent_ok_total": agent_ok_tot,
               "obs_total": obs_tot, "mode_agree": agree_tot,
               "pass": bool(obs_tot) and agent_ok_tot >= codex_ok_tot,
               "note": "预注册口径: 整题全对数 agent >= codex ⇒ 质量不降; 逐题 mode 逐批单列"},
        "H8": {"per_batch": h8_meta, "calls_target": a.calls_target,
               "agent_calls_mean": (sum(a_calls) / len(a_calls)) if a_calls else None,
               "agent_calls_min": min(a_calls) if a_calls else None,
               "agent_calls_max": max(a_calls) if a_calls else None,
               "codex_calls_mean": (sum(c_calls) / len(c_calls)) if c_calls else None,
               "target_met": bool(a_calls) and all(c <= a.calls_target for c in a_calls),
               "coverage_pass": all(m["unmatched"] == 0 and m["ambiguous"] == 0 for m in h8_meta),
               "calls_by_task_sum": {}},
        "H9_cross_time": {"failures": replay_fail, "pass": not replay_fail,
                          "note": "对仓内快照的第二次 check_usage_replay（跨时间, 判分后）"},
        "H10_from_verdicts": {b: (per_batch.get(b, {}).get("criteria") or {}).get("H10")
                              for b in a.batches},
        "all_batches_green": all(r.get("rc") == 0 for r in batch_rows) and bool(batch_rows),
    }
    cbt = {}
    for r in batch_rows:
        for tid, n in (r.get("agent_calls_by_task") or {}).items():
            cbt[tid] = cbt.get(tid, 0) + n
    agg["H8"]["calls_by_task_sum"] = cbt

    out = a.out if os.path.isabs(a.out) else os.path.join(REPO, a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(agg, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    print("=== R505 汇总 (n=%d 批) ===" % len(a.batches))
    for r in batch_rows:
        if r.get("status") == "missing":
            print("  批 %s: 缺产物" % r["batch"])
            continue
        print("  批 %s rc=%d | codex 整题全对 %d/%d calls=%d tok=%d | agent 整题全对 %d/%d calls=%d tok=%d | 红项=%s"
              % (r["batch"], r["rc"], r["codex"]["whole_ok"], r["codex"]["n"], r["codex"]["calls"],
                 r["codex"]["tok"], r["agent"]["whole_ok"], r["agent"]["n"], r["agent"]["calls"],
                 r["agent"]["tok"], r["criteria_fail"] or "-"))
    print("H7 质量面: codex %d/%d | agent %d/%d | mode 一致 %d/%d ⇒ %s"
          % (codex_ok_tot, obs_tot, agent_ok_tot, obs_tot, agree_tot, obs_tot,
             "PASS" if agg["H7"]["pass"] else "NOT"))
    print("H8 调用构成: %s | 本侧调用 均值 %s min %s max %s (目标 ≤%d ⇒ %s)"
          % (h8_meta, agg["H8"]["agent_calls_mean"], agg["H8"]["agent_calls_min"],
             agg["H8"]["agent_calls_max"], a.calls_target,
             "达标" if agg["H8"]["target_met"] else "未达标"))
    print("H8 逐题调用合计: %s" % ", ".join("%s×%d" % (k, v) for k, v in sorted(cbt.items())))
    print("H9 跨时间复核: %s" % ("PASS" if agg["H9_cross_time"]["pass"] else "NOT %s" % replay_fail))
    print("汇总 -> %s" % out)
    return 0 if (agg["all_batches_green"] and agg["H7"]["pass"] and agg["H9_cross_time"]["pass"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())