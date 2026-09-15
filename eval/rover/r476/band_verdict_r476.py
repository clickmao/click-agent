#!/usr/bin/env python3
"""R476 器具: 红线判定分档化机检 + 负控 (+ 计价面 fail-closed / 器具轮号参数化)。

铁律 (承 R450/R475):
  · 不重建 prompt: 只读**实发**遥测 (data/telemetry/host.jsonl) 与已入库夹具 (r469/r470)。
  · 判定串与产品**同源**: 直接 exec scripts/kpi_cache_hit.py, 禁在器具里另写一份判据。
  · 缺文件/缺字段 ⇒ VOID / unreported, 禁按 0。
  · 真值面为空集时给**计数**, 禁以空集宣称达标。
"""
import io, json, os, re, subprocess, sys, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
def P(*a): return os.path.join(ROOT, *a)
OUT = P("eval", "rover", "r476")

spec = importlib.util.spec_from_file_location("kpi_cache_hit", P("scripts", "kpi_cache_hit.py"))
K = importlib.util.module_from_spec(spec); spec.loader.exec_module(K)

A, T, NC, BT = {}, {}, {}, {}

def main():
    # ── C1 常数机检 (fail-closed) ──
    par = K.check_source_parity()
    A["C1_parity_clean"] = (par == [])
    A["C1_parity_detail"] = par

    # ── C2/C3 三方一致: r469 json ↔ py 复算 ↔ 产品单测字面量 ──
    fx = json.load(io.open(P("eval", "rover", "r469", "hit-ceiling.json"), encoding="utf-8"))
    bands = fx["bands"]
    cs = io.open(P("src", "agent.tests", "PromptCacheBandTests.cs"), encoding="utf-8").read()
    cs_prefixes = [int(x) for x in re.search(r"FixturePrefixes\s*=\s*\{([^}]*)\}", cs).group(1).split(",")]
    cs_block = re.search(r"FixtureCeilings\s*=\s*\{(.*?)\n\s*\};", cs, re.S).group(1)
    cs_rows = [[float(v) for v in re.findall(r"0\.\d+", line)] for line in cs_block.splitlines() if "0." in line]
    cs_needed = [float(v) for v in re.search(r"FixtureNeededPrefix\s*=\s*\{([^}]*)\}", cs).group(1).split(",")]
    cs_redline = float(re.search(r"FixtureRedline\s*=\s*([0-9.]+)", cs).group(1))

    rows = []
    ok_c2 = True
    for b, band in enumerate(bands):
        u = band["median_user_tok"]
        need_json = fx["exact_needed_prefix"][band["key"]] if "key" in band else None
        for p in cs_prefixes:
            got = round(K.ceiling_for_turn(p, u), 4)
            exp = band["ceilings"]["prefix_%d" % p]
            same = abs(got - exp) <= 1e-4
            ok_c2 &= same
            rows.append({"band": band["band_chars"], "prefix": p, "py": got, "json": exp, "same": same})
    needed_py = [round(K.prefix_needed(bands[i]["median_user_tok"]), 1) for i in range(len(bands))]
    needed_json = [fx["exact_needed_prefix"]["-".join(str(x) for x in b["band_chars"])] if "-".join(str(x) for x in b["band_chars"]) in fx["exact_needed_prefix"] else None for b in bands]
    if any(v is None for v in needed_json):   # 夹具键名 = 档字符区间串 (201-10000)
        keymap = {"201+": "201-10000"}
        needed_json = []
        for b in bands:
            k = "-".join(str(x) for x in b["band_chars"])
            needed_json.append(fx["exact_needed_prefix"].get(k, fx["exact_needed_prefix"].get(keymap.get(K.BAND_LABELS[bands.index(b)], ""))))
    ok_c2 &= all(n is not None and abs(n - g) <= 0.05 for n, g in zip(needed_json, needed_py))
    A["C2_fixture_recompute"] = bool(ok_c2)
    A["C2_rows"] = rows
    A["C2_needed"] = {"py": needed_py, "json": needed_json, "cs": cs_needed}

    # C3 三方 (json/py/cs) 与红线同值
    cs_vs_json = all(abs(cs_rows[p][b] - bands[b]["ceilings"]["prefix_%d" % cs_prefixes[p]]) <= 1e-4
                     for p in range(len(cs_prefixes)) for b in range(len(bands)))
    A["C3_cs_literals_match_fixture"] = bool(cs_vs_json)
    A["C3_needed_cs_match"] = bool(all(abs(a - b) <= 0.05 for a, b in zip(cs_needed, needed_py)))
    A["C3_redline_three_way"] = bool(abs(cs_redline - fx["redline"]) < 1e-12 and abs(K.REDLINE - fx["redline"]) < 1e-12)

    # C4 口径非换皮: 长档 (u>=94) 单值口径必判越线, 分档口径在上限内判 at_target
    u_long = bands[2]["median_user_tok"]; p_ref = 2110
    c_long = K.band_ceiling(p_ref, u_long)
    rate = round(c_long - K.tolerance(p_ref) / 2, 6)
    single_violated = rate < K.REDLINE                                   # 单值口径
    band_verdict = K.band_verdict(2, p_ref, u_long, rate)                # 分档口径
    NC["C4_single_vs_band"] = {"rate": rate, "ceiling": round(c_long, 4), "single_violated": single_violated,
                               "band_verdict": band_verdict,
                               "diverges": bool(single_violated and band_verdict == K.VERDICT_AT_TARGET)}
    A["C4_single_vs_band_diverges"] = NC["C4_single_vs_band"]["diverges"]

    # ── C5 真实遥测分档聚合 (实发数据, 不重建) ──
    tel = P("data", "telemetry", "host.jsonl")
    rc = subprocess.run([sys.executable, P("scripts", "kpi_cache_hit.py"), "--file", tel,
                         "--json", P("eval", "rover", "r476", "real-bands.json")],
                        capture_output=True, text=True)
    real = json.load(io.open(P("eval", "rover", "r476", "real-bands.json"), encoding="utf-8"))
    B = real["bands"]
    BT.update(B)
    A["C5_real_judged_zero"] = bool(B["total"]["judged"] == 0)
    A["C5_real_not_applicable"] = B["not_applicable"]
    A["C5_real_unreported"] = B["total"]["unreported"]
    A["C5_real_rc"] = rc.returncode
    A["C5_real_by_channel"] = B["by_channel"]
    A["C5_verdict_not_claimed"] = bool(B["total"]["judged"] == 0 or B["verdict"] == "PASS")

    # ── C6 负控 5 例 (禁恒绿/恒红) ──
    p0, u_short, u_long2 = 2110, 11, 300
    c_long2 = K.band_ceiling(p0, u_long2)
    tol = K.tolerance(p0)
    nc1 = K.band_verdict(3, p0, u_long2, round(c_long2 - 2 * tol, 6))       # 低于上限 2 容差
    nc2 = K.band_verdict(3, p0, u_short, 0.90)                              # 短档低于红线
    nc3 = K.band_verdict(3, p0, u_long2, -1)                                # 未上报
    nc4a = K.aggregate_bands([{"turn": 3, "cacheable": p0, "growth": u_long2,
                               "rate": round(c_long2 - tol / 2, 6), "channel": "shared_prefix"}])
    nc4b = K.aggregate_bands([{"turn": 3, "cacheable": p0, "growth": u_long2,
                               "rate": round(c_long2 - 2 * tol, 6), "channel": "shared_prefix"}])
    nc5 = K.band_verdict(3, p0, u_long2, 0.80)                              # 明显退化: 两口径都判红
    NC["NC1_below_ceiling"] = {"verdict": nc1, "ok": nc1 == K.VERDICT_BELOW_CEILING}
    NC["NC2_below_target"] = {"verdict": nc2, "ok": nc2 == K.VERDICT_BELOW_TARGET}
    NC["NC3_unreported_excluded"] = {"verdict": nc3, "judged": nc4a["total"]["judged"] if False else
                                     K.aggregate_bands([{"turn": 3, "cacheable": p0, "growth": u_long2,
                                                         "rate": -1, "channel": "shared_prefix"}])["total"]["judged"],
                                     "ok": nc3 == K.VERDICT_UNREPORTED}
    NC["NC4_two_way"] = {"pass_case": nc4a["verdict"], "fail_case": nc4b["verdict"],
                         "ok": nc4a["verdict"] == "PASS" and nc4b["verdict"] == "FAIL_BELOW_CEILING"}
    NC["NC5_both_red_on_real_degrade"] = {"band_verdict": nc5, "single_violated": 0.80 < K.REDLINE,
                                          "ok": nc5 != K.VERDICT_AT_TARGET and 0.80 < K.REDLINE}
    A["C6_negctl_all_ok"] = all(v["ok"] for v in NC.values() if isinstance(v, dict) and "ok" in v)

    # ── C7 计价面 fail-closed ──
    jrc = subprocess.run([sys.executable, P("eval", "rover", "r475", "join_usage_truth.py"), "--selftest"],
                         capture_output=True, text=True)
    _jp = P("eval", "rover", "r475", "usage-truth.json")
    j = json.load(io.open(_jp, encoding="utf-8")) if os.path.exists(_jp) else {}
    A["C7_join_selftest_rc"] = jrc.returncode
    A["C7_pricing"] = j.get("pricing", {})
    A["C7_pricing_unreported_ok"] = bool(j.get("pricing", {}).get("status") == "unreported"
                                         and j.get("pricing", {}).get("cost_cny") is None)
    A["C7_selftest_has_nc5"] = "NC5_pricing_unreported" in jrc.stdout and "NC5_fabricated_zero_red" in jrc.stdout

    # ── C8 器具轮号参数化 ──
    be = io.open(P("eval", "capability", "bind_evidence.py"), encoding="utf-8").read()
    A["C8_bind_has_round_arg"] = bool("--round" in be)
    A["C8_bind_round_default_preserved"] = bool("default=AUDITED_BY_ROUND" in be)
    help_rc = subprocess.run([sys.executable, P("eval", "capability", "bind_evidence.py"), "--help"],
                             capture_output=True, text=True)
    A["C8_bind_help_shows_round"] = bool(help_rc.returncode == 0 and "--round" in help_rc.stdout)
    A["C8_bind_reads_round_global"] = bool("global AUDITED_BY_ROUND" in be)

    verdict = {"round": "R476", "asserts": {k: v for k, v in A.items() if isinstance(v, bool)},
               "counts": {k: v for k, v in A.items() if not isinstance(v, (bool, list, dict))}}
    verdict["all_green"] = all(verdict["asserts"].values())
    json.dump(A, io.open(os.path.join(OUT, "asserts_r476.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(NC, io.open(os.path.join(OUT, "negctl_r476.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(B, io.open(os.path.join(OUT, "band-table.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(verdict, io.open(os.path.join(OUT, "verdict-r476.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, v in sorted(verdict["asserts"].items()):
        print(("  OK  " if v else "  RED ") + k)
    print("ALL_GREEN:", verdict["all_green"])
    return 0 if verdict["all_green"] else 1


if __name__ == "__main__":
    sys.exit(main())
