#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R448 机检：按 prereg.json 的 C1–C7 算 verdict（不做解释、不做事后加判）。

输入：eval/rover/r448/probe-r448.json（真机 raw）｜corpus.json（含闸读数 + 归档字母第三通道）
      docs/reports/status.json（M20 承重读数，用于事后反事实折算）
输出：eval/rover/r448/verdict-r448.json
"""
import collections
import hashlib
import json
import pathlib
import statistics

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
R = ROOT / "eval/rover/r448"
probe = json.loads((R / "probe-r448.json").read_text(encoding="utf-8"))
corpus = json.loads((R / "corpus.json").read_text(encoding="utf-8"))
prereg = json.loads((R / "prereg.json").read_text(encoding="utf-8"))
status_path = ROOT / "docs/reports/status.json"
status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}

ARMS = ("J0", "T2", "T1", "NC1t")


def by_i(arm):
    return {r["i"]: r for r in probe["arms"].get(arm, [])}


D = {a: by_i(a) for a in ARMS}
idx = sorted(D["J0"])


def letters(d, keys):
    return [d[i].get("letter") for i in keys if i in d]


def frac_parsed(d, keys):
    ls = letters(d, keys)
    return round(sum(1 for x in ls if x in ("C", "A", "N")) / len(ls), 4) if ls else 0.0


def gen_stats(d, keys):
    g = [d[i]["gen"] for i in keys if i in d and isinstance(d[i].get("gen"), int)]
    if not g:
        return {"n": 0}
    return {"n": len(g), "mean": round(statistics.mean(g), 1), "median": statistics.median(g),
            "min": min(g), "max": max(g), "sum": sum(g),
            "tokens_evaluated_sum": sum(d[i].get("tokens_evaluated") or 0 for i in keys if i in d)}


def agree(a, b, keys):
    """逐样本字母相同率；任一侧不可解析计为不一致（口径写死，防事后放宽）。"""
    kk = [i for i in keys if i in a and i in b]
    if not kk:
        return None, 0
    eq = sum(1 for i in kk if a[i].get("letter") is not None and a[i].get("letter") == b[i].get("letter"))
    return round(eq / len(kk), 4), len(kk)


def reason_counts(d, keys):
    return dict(collections.Counter(d[i].get("parse_reason") for i in keys if i in d))


def letter_mix(d, keys):
    return dict(collections.Counter(x for x in letters(d, keys) if x))


arch_keys = [i for i in idx if corpus["pairs"][i].get("archived_letter")]


def arch_of(i):
    return corpus["pairs"][i].get("archived_letter")


def agree_arch(d, keys):
    kk = [i for i in keys if i in d]
    eq = sum(1 for i in kk if d[i].get("letter") == arch_of(i))
    return (round(eq / len(kk), 4) if kk else None), len(kk)


# ─────────────────────────── C1..C7 ───────────────────────────
checks, readings = [], {}

c1_ok = all(frac_parsed(D[a], idx) >= 0.90 for a in ("J0", "T2", "T1")) and len(letter_mix(D["T1"], idx)) >= 2
readings["C1_non_hollow"] = {"parsed": {a: frac_parsed(D[a], idx) for a in ("J0", "T2", "T1")},
                             "letter_mix": {a: letter_mix(D[a], idx) for a in ("J0", "T2", "T1")},
                             "t1_kinds": len(letter_mix(D["T1"], idx))}
checks.append({"id": "C1_non_hollow", "pass": bool(c1_ok)})

gJ0, gT2, gT1 = gen_stats(D["J0"], idx), gen_stats(D["T2"], idx), gen_stats(D["T1"], idx)
ratio_t1 = round(gT1["mean"] / gJ0["mean"], 4) if gJ0.get("mean") else None
readings["C2_gen_cut"] = {"J0": gJ0, "T2": gT2, "T1": gT1, "ratio_T1_over_J0": ratio_t1,
                          "ref_r447_gen_mean_J0": probe.get("ref_r447", {}).get("gen_mean_J0")}
checks.append({"id": "C2_gen_cut", "pass": bool(gT1.get("mean", 1e9) <= 64 and ratio_t1 is not None
                                                 and ratio_t1 <= 0.36)})

ratio_t2 = round(gT2["mean"] / gJ0["mean"], 4) if gJ0.get("mean") else None
ag_T2_J0, n_T2 = agree(D["T2"], D["J0"], idx)
readings["C3_prompt_only"] = {"ratio_T2_over_J0": ratio_t2, "agree_T2_J0": ag_T2_J0, "n": n_T2}
checks.append({"id": "C3_prompt_only", "pass": bool(ratio_t2 is not None and ratio_t2 <= 0.75
                                                     and (ag_T2_J0 or 0) >= 0.90)})

ag_T1_J0, n1 = agree(D["T1"], D["J0"], idx)
ag_T1_arch, na = agree_arch(D["T1"], arch_keys)
readings["C4_equivalence"] = {"agree_T1_J0": ag_T1_J0, "n_pairs": n1,
                              "agree_T1_archived": ag_T1_arch, "n_archived": na,
                              "archived_letters": [arch_of(i) for i in arch_keys],
                              "T1_letters": letters(D["T1"], idx)}
checks.append({"id": "C4_equivalence", "pass": bool((ag_T1_J0 or 0) >= 0.90 and (ag_T1_arch or 0) >= 0.90)})

rc_T1, rc_J0 = reason_counts(D["T1"], idx), reason_counts(D["J0"], idx)
readings["C5_truncation_closed"] = {"T1_reasons": rc_T1, "J0_reasons": rc_J0}
checks.append({"id": "C5_truncation_closed",
               "pass": bool(rc_T1.get("thinking_truncated", 0) == 0 and rc_J0.get("thinking_truncated", 0) >= 1)})

g3 = corpus["gates"]["G3_neg_true_mismatch"]
ag_NC, n_nc = agree(D["NC1t"], D["T1"], sorted(D["NC1t"]))
readings["C6_neg_control"] = {"true_mismatch": g3["true_mismatch"], "n_neg": g3["n_neg"],
                              "agree_NC1t_T1": ag_NC, "n": n_nc,
                              "NC1t_letters": [D["NC1t"][i].get("letter") for i in sorted(D["NC1t"])],
                              "T1_letters_same_idx": [D["T1"].get(i, {}).get("letter") for i in sorted(D["NC1t"])]}
checks.append({"id": "C6_neg_control", "pass": bool(g3["pass"] and
                                                    (ag_NC if ag_NC is not None else 1.0) <= 0.85)})

# C7 记账 / 形态
all_calls = []
for a in ARMS:
    all_calls += [r for r in probe["arms"].get(a, [])]
cache_zero = all(c.get("cache_n") == 0 for c in all_calls)
identity = [c for c in all_calls if isinstance(c.get("tokens_evaluated"), int)
            and isinstance(c.get("timings_prompt_n"), int)]
identity_ok = all(c["tokens_evaluated"] == c["timings_prompt_n"] + (c.get("cache_n") or 0) for c in identity)
pe_equal = {}
for i in idx:
    vals = {a: D[a].get(i, {}).get("tokens_evaluated") for a in ("J0", "T2", "T1")}
    pe_equal[i] = len(set(vals.values())) == 1
argv = probe.get("form", {}).get("argv", [])
argv_ok = all(x in argv for x in ["-np", "1", "f32", "off", "-c", "4608", "--jinja"]) and \
    probe.get("form", {}).get("argv_expected_tail") == ["-c", "4608", "-t", "1", "-np", "1",
                                                        "--cache-type-k", "f32", "--cache-type-v",
                                                        "f32", "--flash-attn", "off", "--jinja"]
c7_ok = cache_zero and identity_ok and all(pe_equal.values()) and argv_ok
readings["C7_accounting_form"] = {"cache_n_zero_all": cache_zero, "n_calls": len(all_calls),
                                  "identity_tested": len(identity), "identity_ok": identity_ok,
                                  "per_sample_prompt_n_equal": f"{sum(pe_equal.values())}/{len(pe_equal)}",
                                  "argv_ok": argv_ok, "argv": argv, "props_ok": "props" in probe.get("form", {})}
checks.append({"id": "C7_accounting_form", "pass": bool(c7_ok)})

all_green = all(c["pass"] for c in checks)
red = [c["id"] for c in checks if not c["pass"]]

# ─────────────────────────── 事后判据（不参与决策） ───────────────────────────
posthoc = []
# CH1: T1 vs R447 解码约束臂（J1 恒 2 tok / 恒 A）
posthoc.append({"id": "CH1_vs_r447_decode_constraint",
                "note": "R447 J1（grammar 单字母）= gen 恒 2、字母恒 A（agree 0.4444）；本轮 T1 保留思考",
                "T1_gen": {"mean": gT1.get("mean"), "max": gT1.get("max")},
                "T1_kinds": len(letter_mix(D["T1"], idx)), "R447_J1_gen_sum": probe.get("ref_r447", {}).get("gen_J1_sum")})
# CH2: J0 是否复现归档（器具漂移告警通道，不 fail-closed）
ag_J0_arch, n_j0a = agree_arch(D["J0"], arch_keys)
posthoc.append({"id": "CH2_J0_faithfulness_vs_archive", "agree_J0_archived": ag_J0_arch, "n": n_j0a,
                "note": "R447 同通道为 12/12；本条为漂移告警，不作 fail-closed"})
# CH3: T1 vs J0 分歧逐条
disagree = [{"i": i, "msg": D["J0"][i].get("msg"), "J0": D["J0"][i].get("letter"),
             "T1": D["T1"][i].get("letter"), "archived": arch_of(i)}
            for i in idx if D["J0"][i].get("letter") != D["T1"][i].get("letter")]
posthoc.append({"id": "CH3_disagreements", "n": len(disagree), "rows": disagree})
# CH4: 反事实收益（仅记录，不计入 KPI）
cells = (status.get("acceptance_matrix") or {}).get("cells") or []
m20 = next((c for c in cells if c.get("grid") == "M20"), None)
if m20 and gJ0.get("mean"):
    A = m20["A_remote"]
    BRJ = m20["BRJ_remote"]
    local_true = (1 - m20["D_remote_plus_local_true_pct"] / 100.0) * A - BRJ
    gen_judge_m20 = 1974          # R446 机制读数：M20 判官本地生成
    saved = gen_judge_m20 * (1 - (gT1["mean"] / gJ0["mean"]))
    new_pct = 1 - (BRJ + local_true - saved) / A
    posthoc.append({"id": "CH4_counterfactual_M20_with_local",
                    "A_remote": A, "BRJ_remote": BRJ, "local_true_derived": round(local_true),
                    "judge_gen_m20": gen_judge_m20, "gen_ratio": round(gT1["mean"] / gJ0["mean"], 4),
                    "saved_local_tok": round(saved),
                    "D_remote_plus_local_true_before_pct": m20["D_remote_plus_local_true_pct"],
                    "D_remote_plus_local_true_after_pct": round(new_pct * 100, 2),
                    "note": "反事实：仅判官生成侧压缩；未计门通道与预填充；不等于实测"})
# CH5: 逐条 T1 内容长度（防「字母对但内容退化成空」）
lens = [len(D["T1"][i].get("content") or "") for i in idx]
posthoc.append({"id": "CH5_T1_content_len", "min": min(lens), "max": max(lens),
                "median": statistics.median(lens)})
# CH6: 记账口径**修正**（C7 的「跨臂 prompt_n 相等」为判定项设计缺陷：T 臂 prompt 比 J0 长 28 字符）
pe_t2t1 = [{"i": i, "T2": D["T2"].get(i, {}).get("tokens_evaluated"),
            "T1": D["T1"].get(i, {}).get("tokens_evaluated")} for i in idx]
posthoc.append({"id": "CH6_accounting_corrected_criterion",
                "defect": "C7 预注册要求「逐样本 prompt_n 跨臂相等」，但 T2/T1 的 prompt 比 J0 多 28 字符"
                          "（限长子句）⇒ 该断言按定义不可能成立（0/18）。属**判定项设计缺陷**，非功能红。",
                "same_prompt_arms": "T2 vs T1",
                "equal_frac": f"{sum(1 for r in pe_t2t1 if r['T2'] == r['T1'])}/{len(pe_t2t1)}",
                "cache_n_zero": cache_zero, "identity_ok": identity_ok, "argv_ok": argv_ok,
                "J0_prompt_n_vs_T_prompt_n_delta_tokens": sorted({(D['J0'].get(i, {}).get('tokens_evaluated') or 0)
                                                                  - (D['T1'].get(i, {}).get('tokens_evaluated') or 0)
                                                                  for i in idx}),
                "rows": pe_t2t1})
# CH7: 跨轮确定性（本轮 J0 与 R447 J0 冻结读数对照，同 prompt 同模型同温度）
posthoc.append({"id": "CH7_determinism_vs_r447",
                "gen_J0_sum_now": gJ0.get("sum"), "gen_J0_sum_r447": probe.get("ref_r447", {}).get("gen_J0_sum"),
                "identical": gJ0.get("sum") == probe.get("ref_r447", {}).get("gen_J0_sum"),
                "agree_J0_archived": ag_J0_arch,
                "note": "同 prompt 同档 ⇒ 逐样本 gen 之和与 R447 存档完全相同 ⇒ 器具可复现（跨轮）"})
# CH8: 限长思考真实长度分布（T2 = 无限长预算，未截断）⇒ 无截断所需预算下界
posthoc.append({"id": "CH8_required_budget_lower_bound",
                "T2_gen": {"median": gT2.get("median"), "max": gT2.get("max"), "mean": gT2.get("mean")},
                "T2_any_truncation": reason_counts(D["T2"], idx).get("thinking_truncated", 0),
                "T1_truncation_rate": round(reason_counts(D["T1"], idx).get("thinking_truncated", 0) / len(idx), 4),
                "note": "限长子句下真实思考长度仍达 T2 的 median 138.5 / max 211 ⇒ 预算 128 必然截断；"
                        "无截断所需预算 >= 212（即现网 512 已不可再压）"})

doc = {"round": "R448", "instrument": "r448_analyze",
       "prereg_sha256": hashlib.sha256((R / "prereg.json").read_bytes()).hexdigest(),
       "prereg_probe_sha256": probe.get("prereg", {}).get("sha256"),
       "prereg_ok": hashlib.sha256((R / "prereg.json").read_bytes()).hexdigest() == probe.get("prereg", {}).get("sha256"),
       "corpus_gates": corpus["gates"], "n_pairs": len(idx), "n_neg": len(D["NC1t"]),
       "criteria": checks, "readings": readings, "cost": {
           "gen_J0_sum": gJ0.get("sum"), "gen_T2_sum": gT2.get("sum"), "gen_T1_sum": gT1.get("sum"),
           "gen_saved_T1_vs_J0": (gJ0.get("sum") or 0) - (gT1.get("sum") or 0),
           "wall_J0_mean": round(statistics.mean([D["J0"][i]["wall_s"] for i in idx if "wall_s" in D["J0"][i]]), 2),
           "wall_T1_mean": round(statistics.mean([D["T1"][i]["wall_s"] for i in idx if "wall_s" in D["T1"][i]]), 2)},
       "checks_posthoc": posthoc, "all_green": all_green, "red_items": red,
       "decision": ("C1..C7 全绿 ⇒ R449 产品化候选（开关默认关 + AOT + M20 三臂真机 A/B）"
                    if all_green else f"存在红项 {red} ⇒ 负结论归档，限长思考不得启用")}
(R / "verdict-r448.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
for c in checks:
    print(f"[{c['id']}] {'PASS' if c['pass'] else 'FAIL'}")
print(json.dumps({k: readings[k] for k in readings}, ensure_ascii=False)[:1200])
print(f"[all_green] {all_green} red={red}")
print(f"[done] {R/'verdict-r448.json'}")
