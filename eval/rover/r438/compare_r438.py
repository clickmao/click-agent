#!/usr/bin/env python3
"""R438 汇总 — 臂矩阵 → 判据 C1–C8 → verdict-summary.json（禁手抄: 全部由 verdict/publish 台账读取）。

臂文件: verdict-<ARM>-<grid><sfx>.json  (run_arm.sh 命名)
输出: eval/rover/r438/verdict-summary.json
"""
import json
import os
import sys

D = os.path.abspath(os.path.dirname(__file__))
P12 = {"A": "verdict-A-p12.json", "B": "verdict-B-p12.json", "BRJ": "verdict-BRJ-p12.json",
       "BRJ2": "verdict-BRJ-p12-2.json", "BP": "verdict-BP-p12.json"}
P8 = {"A": "verdict-A-p8.json", "B": "verdict-B-p8.json", "BRJ": "verdict-BRJ-p8.json"}


def load(name):
    p = os.path.join(D, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def tk(x):
    return x["tokens"] if x and "tokens" in x else (x["tokens_total"] if x else None)


def drop(base, x):
    if not base or not x or not base.get("tokens"):
        return None
    b, xx = tk(base), tk(x)
    return round((b - xx) / b * 100, 2) if b else None


def row(v):
    if not v:
        return None
    return {"calls": v["calls_total"], "G": v["G_calls"], "J": v["J_calls"], "tokens": v["tokens_total"],
            "G_tokens": v["G_tokens"], "J_tokens": v["J_tokens"], "fn": v["fn_n"], "fp": v["fp_n"],
            "acc": v["accuracy"], "unassigned": v["unassigned_calls"], "r1_skips": v["r1_skips"],
            "r1_passes": v["r1_passes"], "judge_local_tokens": v["judge_local_tokens"],
            "judge_local_ms": v["judge_local_ms"], "judge_local_n": v["judge_source_count"]["local"],
            "structural": v["judge_source_count"]["structural_no_request"],
            "rf": v.get("judge_remote_fallback_n", 0),
            "gate_r1_n": len(v["r1_records"]), "bin_sha": v["bin_sha"],
            "S2_delta": v["cross_check_S2"]["delta"], "S1_ok": v["repro_archive_ok"],
            "per_turn_actual": [q["actual"] for q in v["per_turn"]]}


pub = load("publish-info.json") or {}
a12 = load(P12["A"])
rows12 = {k: row(load(f)) for k, f in P12.items()}
rows8 = {k: row(load(f)) for k, f in P8.items()}
for grid, rows in (("p12", rows12), ("p8", rows8)):
    base = rows.get("A")
    for k, r in rows.items():
        if r:
            r["drop_vs_A_pct"] = drop(base, r)
p8base = rows8.get("A")
a8 = load(P8["A"])

def _first(v, key):
    if isinstance(v, list):
        v = v[0] if v else {}
    return (v or {}).get(key)


crit = {}
crit["C1_形态"] = {
    "il_warnings": pub.get("il_warnings"), "native_code": pub.get("native_code"),
    "publish_rc": pub.get("rc_from_log"), "env_i_version_rc": pub.get("env_i_version_rc"),
    "v0_gate_pass": pub.get("v0_gate_pass"), "v0_raw_native_ok": (pub.get("v0_under_test") or {}).get("native_ok"),
    "v0_negative_control_rc": (_first(pub.get("v0_negative_control"), "bare_rc")),
    "bin_sha256": pub.get("sha256"), "bin_bytes": pub.get("bytes"),
    "head": pub.get("head"), "ok": bool(pub.get("il_warnings") == 0 and pub.get("native_code") is True
                                        and pub.get("rc_from_log") == "0" and pub.get("env_i_version_rc") == 0
                                        and pub.get("v0_gate_pass") is True)}
crit["C2_双源一致"] = {"all_S1_ok": all(r["S1_ok"] for r in rows12.values() if r) and all(r["S1_ok"] for r in rows8.values() if r),
                    "all_S2_delta0": all(r["S2_delta"] == 0 for r in rows12.values() if r) and all(r["S2_delta"] == 0 for r in rows8.values() if r),
                    "all_unassigned0": all(r["unassigned"] == 0 for r in rows12.values() if r) and all(r["unassigned"] == 0 for r in rows8.values() if r),
                    "per_arm": {k: {"S1": r["S1_ok"], "S2_delta": r["S2_delta"], "unassigned": r["unassigned"]}
                                for k, r in list(rows12.items()) + list(rows8.items()) if r}}
crit["C3_门质量"] = {"BRJ_p12_acc": rows12["BRJ"]["acc"] if rows12.get("BRJ") else None,
                  "BRJ_p12_fn_fp": [rows12["BRJ"]["fn"], rows12["BRJ"]["fp"]] if rows12.get("BRJ") else None,
                  "ok": bool(rows12.get("BRJ") and rows12["BRJ"]["acc"] == 1.0 and rows12["BRJ"]["fn"] == 0 and rows12["BRJ"]["fp"] == 0)}
crit["C4_主KPI_token降幅"] = {"p12_BRJ_drop_pct": rows12["BRJ"]["drop_vs_A_pct"] if rows12.get("BRJ") else None,
                          "p12_target": 30.0,
                          "p12_ok": bool(rows12.get("BRJ") and rows12["BRJ"]["drop_vs_A_pct"] >= 30.0),
                          "p8_BRJ_drop_pct": rows8["BRJ"]["drop_vs_A_pct"] if rows8.get("BRJ") else None,
                          "p8_ok": bool(rows8.get("BRJ") and rows8["BRJ"]["drop_vs_A_pct"] >= 30.0)}
crit["C4b_降幅分解"] = {
    "门_节省token": (tk(a12) - tk(rows12["B"])) if (a12 and rows12.get("B")) else None,
    "门_占比pct": drop(rows12.get("A"), rows12["B"]) if (a12 and rows12.get("B")) else None,
    "J本地化_节省token": (rows12["B"]["J_tokens"] - rows12["BRJ"]["J_tokens"]) if (rows12.get("B") and rows12.get("BRJ")) else None,
    "J本地化_占比pct": round((rows12["B"]["J_tokens"] - rows12["BRJ"]["J_tokens"]) / tk(a12) * 100, 2) if (a12 and rows12.get("B") and rows12.get("BRJ")) else None,
    "J本地化_远端请求消除数": (rows12["B"]["J"] - rows12["BRJ"]["J"]) if (rows12.get("B") and rows12.get("BRJ")) else None}
crit["C5_单变量_J本地化"] = {"B_J_calls": rows12["B"]["J"] if rows12.get("B") else None,
                        "BRJ_J_calls": rows12["BRJ"]["J"] if rows12.get("BRJ") else None,
                        "BRJ_judge_local_n": rows12["BRJ"]["judge_local_n"] if rows12.get("BRJ") else None,
                        "ok": bool(rows12.get("B") and rows12.get("BRJ") and rows12["BRJ"]["J"] == 0 and rows12["B"]["J"] > 0)}
crit["C6_负控_无设备"] = {"BP_r1_skips": rows12["BP"]["r1_skips"] if rows12.get("BP") else None,
                     "BP_J_remote_calls": rows12["BP"]["J"] if rows12.get("BP") else None,
                     "BP_remote_fallback_n": rows12["BP"]["rf"] if rows12.get("BP") else None,
                     "BP_drop_pct": rows12["BP"]["drop_vs_A_pct"] if rows12.get("BP") else None,
                     "ok": bool(rows12.get("BP") and rows12["BP"]["r1_skips"] == 0 and rows12["BP"]["rf"] > 0
                                and rows12["BP"]["drop_vs_A_pct"] < 0)}
crit["C7_确定性"] = {"BRJ_tokens": rows12["BRJ"]["tokens"] if rows12.get("BRJ") else None,
                  "BRJ2_tokens": rows12["BRJ2"]["tokens"] if rows12.get("BRJ2") else None,
                  "delta_tokens": (rows12["BRJ2"]["tokens"] - rows12["BRJ"]["tokens"]) if (rows12.get("BRJ") and rows12.get("BRJ2")) else None,
                  "same_actual": bool(rows12.get("BRJ") and rows12.get("BRJ2") and rows12["BRJ"]["per_turn_actual"] == rows12["BRJ2"]["per_turn_actual"]),
                  "gate_r1_n": rows12["BRJ"]["gate_r1_n"] if rows12.get("BRJ") else None,
                  "ok": bool(rows12.get("BRJ") and rows12.get("BRJ2")
                             and abs(rows12["BRJ2"]["tokens"] - rows12["BRJ"]["tokens"]) <= 0.01 * a12["tokens_total"]
                             and rows12["BRJ"]["per_turn_actual"] == rows12["BRJ2"]["per_turn_actual"])}
crit["C8_挂载生效"] = {"gate_prompt_len_min": None, "growth_chars_seen": None, "role_seed_chars_seen": None,
                   "ok": False}
if a12:
    v = load(P12["BRJ"])
    gpl = [r["gate_prompt_len"] for r in v["r1_records"]]
    gc = [r["growth_chars"] for r in v["r1_records"]]
    rs = [r["role_seed_chars"] for r in v["r1_records"]]
    crit["C8_挂载生效"] = {"gate_prompt_len_min": min(gpl) if gpl else None, "gate_prompt_len_max": max(gpl) if gpl else None,
                       "growth_chars_seen": sorted(set(gc)), "role_seed_chars_seen": sorted(set(rs)),
                       "n_r1_records": len(gpl),
                       "ok": bool(gpl and min(gpl) > 0 and any(x is not None for x in gc))}

out = {"round": "R438", "bin_sha256": pub.get("bin_sha256"), "head": pub.get("head"),
       "p12_rows": rows12, "p8_rows": rows8, "criteria": crit}
with open(os.path.join(D, "verdict-summary.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print("=== p12 臂矩阵 ===")
for k in ("A", "B", "BRJ", "BRJ2", "BP"):
    r = rows12.get(k)
    print(f"{k:5s} " + ("缺失" if not r else
          f"calls={r['calls']:2d}(G{r['G']}/J{r['J']}) tok={r['tokens']:6d} drop={r['drop_vs_A_pct']:>6}% "
          f"FN={r['fn']} FP={r['fp']} acc={r['acc']:.3f} r1skip={r['r1_skips']} Jloc={r['judge_local_n']}"))
print("=== p8 臂矩阵 ===")
for k in ("A", "B", "BRJ"):
    r = rows8.get(k)
    print(f"{k:5s} " + ("缺失" if not r else
          f"calls={r['calls']:2d}(G{r['G']}/J{r['J']}) tok={r['tokens']:6d} drop={r['drop_vs_A_pct']:>6}% "
          f"FN={r['fn']} FP={r['fp']} acc={r['acc']:.3f} r1skip={r['r1_skips']} Jloc={r['judge_local_n']}"))
print("=== 判据 ===")
for k, v in crit.items():
    print(f"{k}: " + json.dumps({kk: vv for kk, vv in v.items() if kk != 'per_arm'}, ensure_ascii=False))
print(f"[written] {os.path.join(D, 'verdict-summary.json')}")
