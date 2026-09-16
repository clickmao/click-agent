#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R499 汇总器: 逐臂判据 + 跨臂(同窗单变量)对照 + n≥3 离散度 + 报告表落盘 (通用代码逻辑)。

用法:
  python3 analyze_r499.py [--dir eval/rover/r499] [--arms C,P1,P2,P3] [--out eval/rover/r499/analyze_r499.json]
行为:
  · 逐臂调用 judge_paraphrase_r499.py (退出码 0/1/2 如实透传)
  · 臂缺失或判据 rc=2 ⇒ 本轮记 HELD/INVALID, **不得宣称绿**
  · 同窗对照只算 C vs 各 P; 跨轮一律不出数 (禁相减)
退出码: 0 全绿可达; 1 有红; 3 让行/未跑 (臂不全)
"""
import argparse, io, json, os, statistics, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=HERE)
    ap.add_argument("--arms", default="C,P1,P2,P3")
    ap.add_argument("--out", default=os.path.join(HERE, "analyze_r499.json"))
    ap.add_argument("--allow-missing", action="store_true")
    a = ap.parse_args()
    arms = [x for x in a.arms.split(",") if x]
    res, missing = {}, []
    for arm in arms:
        mode = "C" if arm == "C" else "P"
        jp = os.path.join(a.dir, "judge-%s.json" % arm)
        need = os.path.join(a.dir, "turns-%s.jsonl" % arm)
        if not os.path.isfile(need):
            missing.append(arm)
            print("[让行] 臂 %s 无产物 (%s 缺席)" % (arm, os.path.basename(need)))
            continue
        p = subprocess.run([sys.executable, os.path.join(a.dir, "judge_paraphrase_r499.py"),
                            "--dir", a.dir, "--arm", arm, "--mode", mode, "--json", jp],
                           capture_output=True, text=True)
        tail = [l for l in p.stdout.strip().splitlines() if l.startswith(("VERDICT", "J1", "J2a", "J2e", "J3 "))]
        print("--- %s rc=%d" % (arm, p.returncode))
        for l in tail[:10]:
            print("    " + l[:160])
        j = json.load(io.open(jp, encoding="utf-8-sig")) if os.path.isfile(jp) else {}
        res[arm] = {"mode": mode, "rc": p.returncode, "red": j.get("red", []), "info": j.get("info", {})}

    out = {"round": "R499", "arms_run": list(res), "arms_missing": missing, "per_arm": res}
    if not missing:
        c = res["C"]["info"]
        ps = [res[k]["info"] for k in arms if k.startswith("P")]
        rows = []
        for p in ps:
            rows.append({"calls_delta": p.get("calls_dedup", 0) - c.get("calls_dedup", 0),
                         "tokens_delta": p.get("paid_total_tokens", 0) - c.get("paid_total_tokens", 0),
                         "turn8_outcome": p.get("p_turn8_outcome", "?"),
                         "empty_body": p.get("empty_body")})
        def spread(key):
            v = [x.get(key, 0) for x in ps]
            return {"min": min(v), "max": max(v), "median": statistics.median(v)} if v else {}
        out["window"] = {"control": {"calls": c.get("calls_dedup"), "tokens": c.get("paid_total_tokens"),
                                     "turn8_basis": c.get("p_turn8_basis")},
                         "treatment_n": len(ps),
                         "per_arm": rows,
                         "spread_calls": spread("calls_dedup"),
                         "spread_tokens": spread("paid_total_tokens"),
                         "note": "同窗单变量; 跨轮禁相减"}
    with io.open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("WROTE %s arms=%d missing=%d" % (a.out, len(res), len(missing)))
    if missing:
        return 3 if a.allow_missing else 3
    if any(r["rc"] == 2 for r in res.values()):
        return 1
    return 0 if all(r["rc"] == 0 for r in res.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
