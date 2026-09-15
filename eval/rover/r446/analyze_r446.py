#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R446: 判官 prompt 紧凑变体 —— 同网格三臂比对 (A 分母 / BRJ 基线 / BRJC 紧凑).

用法: python3 analyze_r446.py <dir> <grid> <sfx_A> <sfx_B> <sfx_C>
判据 (预注册见 docs/plans/v0.66.0-r446-*.md §3):
  D1 字母逐轮一致: BRJC vs BRJ 判官字母序列逐轮相同
  D2 判官本地真值降幅: sigma(ev+gen) over judge local rows, BRJC < BRJ (>=10%)
  D3 生成 token 不升: sigma(gen) BRJC <= BRJ
  D4 远端 token 零回归: BRJC remote == BRJ remote
  D5 含本地真值 KPI: 1 - (BRJC成本)/(A成本), 同网格实测分母
  N1 形态负控: 每条臂都存在 local judge 行 (否则空心)
"""
import json
import pathlib
import sys
from collections import Counter


def kv_rows(tele):
    """读遥测 host.jsonl -> [kv dict] (point 事件)."""
    out = []
    p = pathlib.Path(tele)
    if not p.exists():
        return out
    for ln in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        ln = ln.strip()
        if not ln or not ln.startswith("{"):
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        kv = d.get("kv") if isinstance(d.get("kv"), dict) else d
        kv = dict(kv)
        kv["_point"] = d.get("point") or kv.get("point") or ""
        out.append(kv)
    return out


def num(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def remote_tokens(calls):
    """远端(桩)真值: prompt+completion 估算之和 + 请求数."""
    tot, n = 0.0, 0
    p = pathlib.Path(calls)
    if not p.exists():
        return 0.0, 0
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        n += 1
        tot += num(d.get("prompt_tokens_est")) + num(d.get("completion_tokens_est"))
    return tot, n


def arm_stats(d, arm, grid, sfx):
    """单臂汇总: 远端桩真值 + 本地通道路径真值 + 判官字母序列."""
    rundir = pathlib.Path(d) / f"run-{arm}-{grid}{sfx}"
    tele = rundir / "data/telemetry/host.jsonl"
    rows = kv_rows(tele)
    # R446: 本地真值口径 = **所有带真值 token 的本地行**(门 local_turn_gate + 判官 correction_judge);
    # 门行不带 source 字段 ⇒ 不能按 source 过滤(否则漏门侧成本, D5 分母失真)。
    local = [r for r in rows if num(r.get("tokens_evaluated"), -1) >= 0]
    gate_local = [r for r in local if "gate" in str(r.get("_point", ""))]
    # 判官行: point/domain 含 judge, 或 kv 带 kind+letter
    jrows = [r for r in rows if "judge" in str(r.get("_point", "")) + str(r.get("domain", ""))
             or (r.get("kind") and r.get("letter") is not None)]
    jloc = [r for r in jrows if str(r.get("source")) == "local"]
    rem, ncall = remote_tokens(pathlib.Path(d) / f"calls-{arm}-{grid}{sfx}.jsonl")
    lt = sum(num(r.get("tokens_evaluated")) + num(r.get("gen_tokens")) for r in local if num(r.get("tokens_evaluated"), -1) >= 0)
    jt = sum(num(r.get("tokens_evaluated")) + num(r.get("gen_tokens")) for r in jloc if num(r.get("tokens_evaluated"), -1) >= 0)
    return {
        "arm": arm, "remote": rem, "remote_calls": ncall, "local_total": lt,
        "local_rows": len(local), "judge_all": len(jrows), "judge_local": len(jloc),
        "judge_tok": jt,
        "judge_prompt": sum(num(r.get("tokens_evaluated")) for r in jloc),
        "judge_gen": sum(num(r.get("gen_tokens")) for r in jloc),
        "letters": [str(r.get("letter") or "?") for r in jloc],
        "msg_heads": [str(r.get("msg_head") or "?") for r in jloc],
        "kinds": [str(r.get("kind") or "?") for r in jloc],
        "cost": rem + lt,
        "gate_tok": sum(num(r.get("tokens_evaluated")) + num(r.get("gen_tokens")) for r in gate_local),
        "by_point": dict(sorted(Counter(str(r.get("_point")) for r in local).items())),
    }


def main():
    d, grid, sA, sB, sC = sys.argv[1:6]
    a = arm_stats(d, "A", grid, sA)
    b = arm_stats(d, "BRJ", grid, sB)
    c = arm_stats(d, "BRJC", grid, sC)
    for x in (a, b, c):
        print(f"[{x['arm']:4}] remote={x['remote']:.0f}(calls={x['remote_calls']}) "
              f"local={x['local_total']:.0f}({x['local_rows']}行) judge_loc={x['judge_local']} "
              f"judge_tok={x['judge_tok']:.0f}(ev={x['judge_prompt']:.0f}+gen={x['judge_gen']:.0f}) "
              f"cost={x['cost']:.0f}")
    print("[BRJ 字母 ]", "".join(b["letters"]))
    print("[BRJC 字母]", "".join(c["letters"]))

    kpi_b = 1 - b["cost"] / a["cost"] if a["cost"] else float("nan")
    kpi_c = 1 - c["cost"] / a["cost"] if a["cost"] else float("nan")
    checks = {
        "D1_字母逐轮一致": {"pass": b["letters"] == c["letters"],
                            "brj": "".join(b["letters"]), "brjc": "".join(c["letters"])},
        "D2_判官本地降幅>=10%": {"pass": (b["judge_tok"] > 0 and c["judge_tok"] <= b["judge_tok"] * 0.9),
                                 "brj": b["judge_tok"], "brjc": c["judge_tok"]},
        "D3_生成不升": {"pass": c["judge_gen"] <= b["judge_gen"], "brj": b["judge_gen"], "brjc": c["judge_gen"]},
        "D4_远端零回归": {"pass": c["remote"] == b["remote"], "brj": b["remote"], "brjc": c["remote"]},
        "N1_非空心": {"pass": min(b["judge_local"], c["judge_local"]) >= 3,
                      "brj": b["judge_local"], "brjc": c["judge_local"]},
    }
    # D1b (事后判据 checks_posthoc, R判据纪律: 预注册 D1 已 FAIL ⇒ 不得改口径, 只补对齐后的读数)
    mb = {h: l for h, l in zip(b["msg_heads"], b["letters"])}
    mc = {h: l for h, l in zip(c["msg_heads"], c["letters"])}
    common = [h for h in mb if h in mc]
    agree = [h for h in common if mb[h] == mc[h]]
    posthoc_d1b = {"n_common_msgs": len(common), "n_agree": len(agree),
                   "agree_rate": (len(agree) / len(common)) if common else None,
                   "diffs": {h[:18]: (mb[h], mc[h]) for h in common if mb[h] != mc[h]}}
    out = {"dir": d, "grid": grid, "arms": {"A": a, "BRJ": b, "BRJC": c},
           "checks_posthoc": {"D1b_按msg_head对齐一致率": posthoc_d1b},
           "kpi_brj": kpi_b, "kpi_brjc": kpi_c, "checks": checks}
    print(f"[KPI 含本地真值] BRJ={kpi_b*100:.2f}%  BRJC={kpi_c*100:.2f}%   (A={a['cost']:.0f})")
    vp = pathlib.Path(d) / f"verdict-r446-analysis-{grid}.json"
    vp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    bad = [k for k, v in checks.items() if not v["pass"]]
    for k, v in checks.items():
        print(("  PASS " if v["pass"] else "  FAIL ") + k + " " + json.dumps(
            {kk: vv for kk, vv in v.items() if kk != "pass"}, ensure_ascii=False))
    print(f"[事后] D1b 按 msg_head 对齐: 共同 {posthoc_d1b['n_common_msgs']} 条, 一致 {posthoc_d1b['n_agree']} "
          f"(rate={posthoc_d1b['agree_rate']}) diffs={posthoc_d1b['diffs']}")
    print(f"[verdict] {vp}")
    return 0 if not bad else 2


if __name__ == "__main__":
    sys.exit(main())
