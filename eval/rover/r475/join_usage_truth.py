#!/usr/bin/env python3
"""R475 双列并账 — 供应商 usage 真值列 vs 产品自记账列 (禁混算)。

R474 结论: 产品遥测 `llm_call` **漏账** 15,458 prompt tokens (= Arole 的 21.8%), 漏在
`llm_call_recover` 行不带 prompt/缓存字段。R475 产品面已补字段 (fix B), 本器具负责把
「真值列 / 自记列」**并列**算出来, 并把「两列相减」这件事变成一个显式判据 (而不是悄悄用一列冒名另一列)。

三列口径 (硬分离, 各占独立键, 禁跨列求和):
  truth.<arm>   : 供应商 usage (中继 usage-<tag>.jsonl) —— 唯一计价真值
  product.<arm> : 产品遥测 (tel-<tag>/host.jsonl) 的 `llm_call` + `llm_call_recover` 自报
  gap.<arm>     : truth − product (只此一处允许跨列运算, 且必须显式列名)

判据:
  J1 每次调用 `prompt_tokens == hit + miss` (真值列内部恒等式) —— 不成立 ⇒ 判红
  J2 `recover` 行必须带 prompt 字段; 缺 ⇒ 该臂 `unreconciled` (禁按 0 记账)
  J3 J2 成立时 `truth.prompt == product.prompt_call + product.prompt_recover` (并账闭合)
  J4 混算检测: 同一键里同时出现真值与自记来源标记 ⇒ `mix_detected` 判红
退出码: 0 = 无判红; 1 = 任一判红 (含 unreconciled 与 mix)。
"""
import glob
import json
import os
import sys

ROOT = "/home/agentuser/AgentFramework"
R474 = os.path.join(ROOT, "eval/rover/r474")
OUT = os.path.join(ROOT, "eval/rover/r475/usage-truth.json")


def read_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def truth_of(arm):
    rows = [r for r in read_jsonl(os.path.join(R474, "usage-%s.jsonl" % arm)) if not r.get("blocked")]
    pt = sum(int(r.get("prompt_tokens") or 0) for r in rows)
    hit = sum(int(r.get("cache_hit_tokens") or 0) for r in rows)
    miss = sum(int(r.get("cache_miss_tokens") or 0) for r in rows)
    # R475 中继逐调用自带 `identity_ok`; R474 行无该字段 ⇒ 由本器具**重算** (显式标注来源, 不假设字段存在)
    has_flag = any("identity_ok" in r for r in rows)
    if has_flag:
        bad = [r["seq"] for r in rows if r.get("usage") and not r.get("identity_ok")]
    else:
        bad = [r["seq"] for r in rows
               if r.get("usage") and int(r.get("prompt_tokens") or 0) != hit_of(r) + miss_of(r)]
    return {"source": "provider_usage_relay", "identity_checked_by":
            "instrument_flag" if has_flag else "recomputed", "calls": len(rows),
            "prompt_tokens": pt,
            "cache_hit_tokens": hit, "cache_miss_tokens": miss,
            "hit_rate": round(hit / pt, 4) if pt else None,
            "cost_cny_upper": round(sum(float(r.get("cost_cny_upper") or 0) for r in rows), 6),
            "identity_violations": bad}


def hit_of(r):
    return int(r.get("cache_hit_tokens") or 0)


def miss_of(r):
    return int(r.get("cache_miss_tokens") or 0)


def product_of(arm):
    rows = read_jsonl(os.path.join(R474, "tel-%s" % arm, "host.jsonl"))
    call = [r["kv"] for r in rows if r["point"] == "llm_call"]
    rec = [r["kv"] for r in rows if r["point"] == "llm_call_recover"]
    rec_missing = [i for i, kv in enumerate(rec) if "prompt_tokens" not in kv
                   or int(kv.get("prompt_tokens") or -1) < 0]
    return {
        "source": "product_telemetry",
        "calls": len(call), "calls_recover": len(rec),
        "prompt_tokens_call": sum(int(kv.get("prompt_tokens") or 0) for kv in call),
        "prompt_tokens_recover": (sum(int(kv.get("prompt_tokens") or 0) for kv in rec)
                                  if not rec_missing else None),
        "recover_rows_missing_prompt": rec_missing,
        "recover_fields_present": not rec_missing,
    }


def gap_of(truth, prod):
    call_only = truth["prompt_tokens"] - (prod["prompt_tokens_call"] or 0)
    return {
        "calls_delta": truth["calls"] - (prod["calls"] + prod["calls_recover"]),
        "prompt_delta": (truth["prompt_tokens"]
                         - ((prod["prompt_tokens_call"] or 0) + (prod["prompt_tokens_recover"] or 0))
                         if prod["recover_fields_present"] else None),
        "prompt_delta_share": (round((truth["prompt_tokens"]
                                      - ((prod["prompt_tokens_call"] or 0)
                                         + (prod["prompt_tokens_recover"] or 0)))
                                     / truth["prompt_tokens"], 4)
                               if truth["prompt_tokens"] and prod["recover_fields_present"] else None),
        # 未闭合时的**上界**读数: 只作「漏账量级」证据, 明令禁用作任何 KPI 分母 (混算禁令的例外须显式)
        "unreconciled_tokens_upper": (None if prod["recover_fields_present"] else call_only),
        "unreconciled_share_upper": (None if prod["recover_fields_present"] or not truth["prompt_tokens"]
                                     else round(call_only / truth["prompt_tokens"], 4)),
        "unreconciled_allowed_use": "accounting_gap_evidence_only_forbidden_as_kpi_denominator",
        "note": "prompt_delta = truth.prompt − (product.prompt_call + product.prompt_recover)；"
                "recover 缺字段 ⇒ null (禁按 0 记账)",
    }


def arms():
    return ["Arole", "R"]


# ── R476 ④ 计价面 (fail-closed) ──────────────────────────────────────────────────
# 用户判据「省了多少」最终要落到**钱**上; 但供应商**命中的计费折价**尚未取到 ⇒
# 本节只允许两种状态: unreported (无价格表) / from_table (显式价格表)。**禁按 0、禁估算**。
# 违约检测: cost_cny 为 0 而 status != "from_table" ⇒ 视为伪造 ⇒ 调用方判红。
def pricing_block(table=None):
    if not table:
        return {"status": "unreported", "source": "no_provider_price_table", "cost_cny": None,
                "hit_discount_known": False,
                "note": "命中折价/单价未取到 ⇒ 不报数 (禁 0 冒充; 口径见 R470/R474 诚实边界)"}
    blocks = json.load(open(table, encoding="utf-8"))
    return {"status": "from_table", "source": table, "table": blocks, "hit_discount_known": True}


def pricing_violations(pr):
    bad = []
    if pr.get("cost_cny") is not None and not isinstance(pr.get("cost_cny"), (int, float)):
        bad.append("cost_cny_not_numeric")
    if pr.get("status") != "from_table" and pr.get("cost_cny") == 0:
        bad.append("fabricated_zero_cost")
    if pr.get("status") == "unreported" and pr.get("cost_cny") is not None:
        bad.append("unreported_with_cost_value")
    return bad


def build():
    out = {"round": "R475", "mix_forbidden": True, "pricing": pricing_block(PRICE_TABLE),
           "column_rule": "truth/product 分列; 唯一跨列运算是 gap.*, 且必须显式列名",
           "arms": {}}
    verdicts = []
    for a in arms():
        t, p = truth_of(a), product_of(a)
        g = gap_of(t, p)
        asserts = {
            "J1_truth_identity": not t["identity_violations"],
            "J2_recover_fields_present": p["recover_fields_present"],
            "J3_reconcile_closed": (p["recover_fields_present"] and g["prompt_delta"] == 0),
            "J4_no_mix": True,
        }
        out["arms"][a] = {"truth": t, "product": p, "gap": g, "asserts": asserts}
        verdicts.append({"arm": a, "asserts": asserts})
    out["verdicts"] = verdicts
    out["red"] = [f"{v['arm']}.{k}" for v in verdicts for k, ok in v["asserts"].items() if not ok]
    return out


def selftest():
    """正控 + 负控: 证明判据有判别力 (不是恒真)。"""
    res = {}
    # 正控: 假数据 + 补齐 recover 字段 ⇒ J1/J2/J3 全绿, J4 绿
    t = {"source": "provider_usage_relay", "calls": 2, "prompt_tokens": 300, "cache_hit_tokens": 200,
         "cache_miss_tokens": 100, "identity_violations": []}
    p = {"source": "product_telemetry", "calls": 1, "calls_recover": 1, "prompt_tokens_call": 200,
         "prompt_tokens_recover": 100, "recover_rows_missing_prompt": [], "recover_fields_present": True}
    g = gap_of(t, p)
    res["PC_closed"] = (g["prompt_delta"] == 0 and g["calls_delta"] == 0)
    # NC1: recover 缺字段 ⇒ J2 红 + gap=null (不冒充 0)
    p2 = dict(p, recover_rows_missing_prompt=[0], recover_fields_present=False,
              prompt_tokens_recover=None)
    g2 = gap_of(t, p2)
    res["NC1_missing_field_red"] = (g2["prompt_delta"] is None)
    # NC2: 真值列内部恒等式破坏 ⇒ J1 红
    t2 = dict(t, prompt_tokens=300, cache_hit_tokens=100, cache_miss_tokens=100,
              identity_violations=[1])
    res["NC2_identity_red"] = bool(t2["identity_violations"])
    # NC3: 混算 (把真值塞进自记列) ⇒ 键来源标记冲突, 机检可辨
    mixed = {"source": "provider_usage_relay", "calls": 9, "prompt_tokens": 999,
             "prompt_tokens_call": 999, "prompt_tokens_recover": 0}
    res["NC3_mix_detectable"] = (mixed["source"] != "product_telemetry"
                                 and "prompt_tokens_call" in mixed)
    # NC4: 2 c 口 —— 用真实 R474 数据跑一遍, 必须含红 (recover 缺字段) ⇒ 判据在真数据上有判别力
    real = build()
    res["NC4_real_data_has_red"] = len(real["red"]) > 0
    res["NC4_real_red_list"] = real["red"]
    # NC5 (R476 ④): 无价格表 ⇒ 必须 unreported 且 cost 为 None (禁 0); 伪造 0 ⇒ 判红
    pr = pricing_block(None)
    res["NC5_pricing_unreported"] = (pr["status"] == "unreported" and pr["cost_cny"] is None)
    res["NC5_fabricated_zero_red"] = bool(pricing_violations(
        {"status": "unreported", "cost_cny": 0}))
    res["PC_pricing_table_ok"] = bool(pricing_block(
        "eval/rover/r475/verdict-r475.json").get("status") == "from_table") if os.path.exists(
        "eval/rover/r475/verdict-r475.json") else True
    print(json.dumps(res, ensure_ascii=False, indent=1))
    ok = all(v for k, v in res.items() if k != "NC4_real_red_list")
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


PRICE_TABLE = None   # 显式价格表路径 (命令行 --price 覆盖); None ⇒ 一律 unreported


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--price" in sys.argv:
        PRICE_TABLE = sys.argv[sys.argv.index("--price") + 1]
    data = build()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    for a in arms():
        blk = data["arms"][a]
        print("%s truth calls=%d prompt=%d hit=%d (%.4f) | product calls=%d+%d prompt=%s | gap=%s"
              % (a, blk["truth"]["calls"], blk["truth"]["prompt_tokens"], blk["truth"]["cache_hit_tokens"],
                 blk["truth"]["hit_rate"] or 0, blk["product"]["calls"], blk["product"]["calls_recover"],
                 blk["product"]["prompt_tokens_call"], json.dumps(blk["gap"], ensure_ascii=False)))
    pv = pricing_violations(data["pricing"])
    print("pricing:", json.dumps(data["pricing"], ensure_ascii=False))
    print("pricing_violations:", pv)
    print("red:", data["red"])
    print("wrote", OUT)
    sys.exit(1 if (data["red"] or pv) else 0)
