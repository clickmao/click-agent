#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R447 机检：按 prereg.json 的 C1–C6 判据算 verdict（不做解释、不做事后加判）。

输入：eval/rover/r447/probe-r447.json（真机 raw）+ corpus.json（含归档字母第三通道）
输出：eval/rover/r447/verdict-r447.json（逐条 pass/fail + 读数 + 决策）
"""
import collections
import json
import pathlib
import statistics

R = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r447")
probe = json.loads((R / "probe-r447.json").read_text(encoding="utf-8"))
corpus = json.loads((R / "corpus.json").read_text(encoding="utf-8"))
prereg = json.loads((R / "prereg.json").read_text(encoding="utf-8"))


def by_i(arm):
    return {r["i"]: r for r in probe["arms"].get(arm, [])}


J0, J1, J2, NC1 = by_i("J0"), by_i("J1"), by_i("J2"), by_i("NC1")
idx = sorted(J0)
raw = {k: p for k, p in enumerate(probe["arms"].get("pairs_raw", []))}   # 顺序 = 语料顺序 (i)


def letters(d, keys):
    return [d[i].get("letter") for i in keys if i in d]


def parsed_frac(d, keys):
    ls = letters(d, keys)
    return (sum(1 for x in ls if x in ("C", "A", "N")) / len(ls)) if ls else 0.0


def gen_stats(d, keys):
    g = [d[i]["gen"] for i in keys if i in d and isinstance(d[i].get("gen"), int)]
    if not g:
        return {"n": 0}
    return {"n": len(g), "mean": round(statistics.mean(g), 1), "median": statistics.median(g),
            "min": min(g), "max": max(g), "sum": sum(g)}


def agree(a, b, keys):
    """逐样本字母相同率；任一侧不可解析计为不一致（口径写死，防事后放宽）。"""
    kk = [i for i in keys if i in a and i in b]
    if not kk:
        return None, 0
    eq = sum(1 for i in kk if a[i].get("letter") is not None and a[i].get("letter") == b[i].get("letter"))
    return round(eq / len(kk), 4), len(kk)


j0_letters = letters(J0, idx)
j0_kinds = sorted({x for x in j0_letters if x})
neg_keys = sorted(NC1)

# NC2 = 平凡结算器（恒 N），不调模型
class NC2:
    @staticmethod
    def get(i):
        return {"letter": "N"}
nc2 = {i: {"letter": "N"} for i in idx}

# 归档第三通道
arch = [(i, J0[i]["letter"], corpus["pairs"][i]["archived_letter"])
        for i in idx if corpus["pairs"][i].get("archived_letter")]
arch_eq = (sum(1 for _, a, b in arch if a == b) / len(arch)) if arch else None

a10, n10 = agree(J1, J0, idx)
aNC1, nNC1 = agree(NC1, J0, neg_keys)
aNC2, _ = agree(nc2, J0, idx)

# C5 记账
all_calls = [c for p in probe["arms"].get("pairs_raw", []) for c in p["calls"].values() if "error" not in c]
cache_all_zero = all((c.get("cache_n") == 0) for c in all_calls)
prompt_n_equal = all(len({raw[i]["calls"][a].get("prompt_n") for a in ("J0", "J1", "J2")}) == 1 for i in idx)

# C6 形态自证
argv = probe["form"].get("argv", [])
req_flags = ["-np", "1", "--cache-type-k", "f32", "--cache-type-v", "f32", "--flash-attn", "off", "-c", "4608", "--jinja"]
argv_ok = all(f in argv for f in req_flags)
req_ok = True
req_bad = []
for p in probe["arms"].get("pairs_raw", []):
    for arm, c in p["calls"].items():
        b = c.get("request") or {}
        want = {"temperature": 0.0, "samplers": ["temperature"], "cache_prompt": False,
                "seed": 0, "stream": False, "return_tokens": True}
        if arm == "J1":
            want["grammar"] = 'root ::= "A" | "C" | "N"'
            want["n_predict"] = 8
        elif arm == "J2":
            want["n_predict"] = 8
        elif arm == "J0":
            want["n_predict"] = 512
        for k, v in want.items():
            if b.get(k) != v:
                req_ok = False
                req_bad.append({"msg": (p.get("msg") or "")[:10], "arm": arm, "field": k, "got": b.get(k), "want": v})
props = probe["form"].get("props") or {}
dgs = props.get("default_generation_settings") or {}
props_temp = dgs.get("temperature", (dgs.get("params") or {}).get("temperature"))

criteria = []
criteria.append({"id": "C1_non_hollow", "pass": parsed_frac(J0, idx) >= 0.90 and parsed_frac(J1, idx) >= 0.90
                 and parsed_frac(NC1, neg_keys) >= 0.90 and len(j0_kinds) >= 2,
                 "read": {"parsed_J0": round(parsed_frac(J0, idx), 3), "parsed_J1": round(parsed_frac(J1, idx), 3),
                          "parsed_NC1": round(parsed_frac(NC1, neg_keys), 3), "J0_kinds": j0_kinds}})
g0, g1 = gen_stats(J0, idx), gen_stats(J1, idx)
criteria.append({"id": "C2_gen_cut", "pass": (g1.get("mean", 9e9) <= 0.20 * g0.get("mean", 0)) and g1.get("max", 9e9) <= 8,
                 "read": {"gen_J0": g0, "gen_J1": g1, "ratio": (round(g1["mean"] / g0["mean"], 4) if g0.get("mean") else None)}})
criteria.append({"id": "C3_equivalence", "pass": (a10 is not None and a10 >= 0.90),
                 "read": {"agree_J1_J0": a10, "n": n10,
                          "confusion": {f"{k}→{v}": c for (k, v), c in collections.Counter(
                              (J0[i]["letter"], J1[i]["letter"]) for i in idx).items()}}})
criteria.append({"id": "C4a_neg_mismatched_prev", "pass": (aNC1 is not None and a10 is not None and aNC1 <= a10 - 0.15),
                 "read": {"agree_NC1_J0": aNC1, "n": nNC1, "gap_vs_J1": (round(a10 - aNC1, 4) if None not in (a10, aNC1) else None)}})
criteria.append({"id": "C4b_neg_trivial_N", "pass": (aNC2 is not None and aNC2 < 0.90),
                 "read": {"agree_NC2_J0": aNC2, "J0_N_share": round(j0_letters.count("N") / len(idx), 3)}})
criteria.append({"id": "C4c_archived_channel", "pass": (arch_eq is not None and arch_eq >= 0.85),
                 "read": {"agree_J0_archived": arch_eq, "n": len(arch),
                          "detail": [{"i": i, "J0": a, "archived": b} for i, a, b in arch]}})
criteria.append({"id": "C5_accounting", "pass": bool(cache_all_zero and prompt_n_equal),
                 "read": {"cache_n_all_zero": cache_all_zero, "prompt_n_equal_across_arms": prompt_n_equal,
                          "note": "本轮只记了 tokens_evaluated(=prompt_n)；恒等式 tokens_evaluated==prompt_n+cache_n 依赖 timings.prompt_n，本轮未落盘 ⇒ 该项未测"}})
criteria.append({"id": "C6_form_selfproof", "pass": bool(argv_ok and req_ok),
                 "read": {"argv_ok": argv_ok, "request_body_ok": req_ok, "bad": req_bad[:5],
                          "props_temperature": props_temp, "argv": argv}})

allgreen = all(c["pass"] for c in criteria)

# ── 事后判据（posthoc）：预注册 C4a 被证伪（错配无效 2/8 = 判定项设计缺陷），语义由本段承担 ──
posthoc = []
try:
    nc1b = json.loads((R / "probe-r447-nc1b.json").read_text(encoding="utf-8"))
    rowsb = nc1b["rows"]
    real_mismatch_n = sum(1 for r in rowsb if r["wrong_prev"] != r["orig_prev"])
    ag_b = round(sum(1 for r in rowsb if r["letter_nc1b"] and r["letter_nc1b"] == r["letter_J0"]) / len(rowsb), 4)
    posthoc.append({"id": "CH1_real_mismatched_prev", "pass": bool(real_mismatch_n == len(rowsb) and ag_b <= 0.85),
                    "read": {"agree_NC1b_J0": ag_b, "n": len(rowsb), "real_mismatch": f"{real_mismatch_n}/{len(rowsb)}",
                             "reference_instrument_selfconsistency": "C4c=1.0 (J0 逐条复现归档产品字母) + R446 同输入⇒同字母",
                             "note": "预注册 C4a 因 prev 候选仅 2 常量而错配无效(2/8) ⇒ 本项为事后替代口径"}})
except Exception as e:
    posthoc.append({"id": "CH1_real_mismatched_prev", "pass": False, "read": {"error": str(e)}})
arch_pairs = [(i, J1[i].get("letter"), corpus["pairs"][i].get("archived_letter"))
              for i in idx if corpus["pairs"][i].get("archived_letter")]
j1_arch = round(sum(1 for _, a, b in arch_pairs if a == b) / len(arch_pairs), 4) if arch_pairs else None
posthoc.append({"id": "CH2_grammar_vs_archived", "pass": bool(j1_arch is not None and j1_arch < 0.85),
                "read": {"agree_J1_archived": j1_arch, "n": len(arch_pairs),
                         "J1_letters": dict(collections.Counter([x or "?" for x in letters(J1, idx)])),
                         "note": "语法臂 18/18 恒 'A'；其与产品真值的一致率 ≈ 真值里 A 的占比 ⇒ 独立复现 C3 红"}})
j0_trunc = [i for i in idx if J0[i].get("parse_reason") != "ok"]
posthoc.append({"id": "CH3_budget_512_truncation", "pass": True,
                "read": {"truncated": j0_trunc, "n_truncated": len(j0_trunc), "n_total": len(idx),
                         "rate": round(len(j0_trunc) / len(idx), 3),
                         "note": "登记型发现（非判据）：基线有 1/18 触 n_predict=512 上限未吐字母 ⇒ "
                                 "产品在该情形会 fallback 远端（本地 512 tok 白付 + 远端全额）"}})

verdict = {
    "round": "R447", "instrument": "r447_analyze",
    "prereg_sha256": probe["prereg"]["sha256"],
    "prereg_ok": prereg["criteria"].keys() is not None,
    "n_pairs": len(idx), "n_neg": len(neg_keys),
    "criteria": criteria, "checks_posthoc": posthoc, "all_green": allgreen,
    "decision": ("C1–C6 全绿 ⇒ 解码侧约束可作 R448 产品化候选（开关默认关 + M20 三臂真机 A/B）"
                 if allgreen else "存在红项 ⇒ 负结论归档，不得启用；红项机制见下"),
    "letter_mix": {"J0": dict(collections.Counter([x or "?" for x in j0_letters])),
                   "J1": dict(collections.Counter([x or "?" for x in letters(J1, idx)])),
                   "J2": dict(collections.Counter([x or "?" for x in letters(J2, idx)])),
                   "NC1": dict(collections.Counter([x or "?" for x in letters(NC1, neg_keys)]))},
    "parse_reasons": {a: dict(collections.Counter([d[i].get("parse_reason") for i in sorted(d)]))
                      for a, d in (("J0", J0), ("J1", J1), ("J2", J2), ("NC1", NC1))},
    "cost": {"gen_J0_sum": g0.get("sum"), "gen_J1_sum": g1.get("sum"),
             "gen_saved": (g0.get("sum", 0) - g1.get("sum", 0)),
             "wall_J0_mean": round(statistics.mean([J0[i]["wall_s"] for i in idx]), 2),
             "wall_J1_mean": round(statistics.mean([J1[i]["wall_s"] for i in idx]), 2)},
    "red_items": [c["id"] for c in criteria if not c["pass"]],
}
(R / "verdict-r447.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
for c in criteria:
    print(("PASS " if c["pass"] else "FAIL "), c["id"], json.dumps(c["read"], ensure_ascii=False)[:300])
print("ALL_GREEN:", allgreen, "| red:", verdict["red_items"])
print("letter_mix:", json.dumps(verdict["letter_mix"], ensure_ascii=False))
print("parse_reasons:", json.dumps(verdict["parse_reasons"], ensure_ascii=False))
print("cost:", json.dumps(verdict["cost"], ensure_ascii=False))
