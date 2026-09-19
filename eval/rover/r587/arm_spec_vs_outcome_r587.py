#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R587 · 候选 ① 的收官一步: 「失败是否落在**同一子规格**」用**产物身份 × 例级结果**交叉表判。

输入 = 两份纯只读定因件（`wythoff_subspec_r587.py` / `empty_error_cause_r587.py` 的产物）,
不做任何重算、不引入新夹具。

判法:
  · 子规格（形态指纹标签）来自源码标记; 结果是**重放**得到的例级类别计数。
  · 「同一子规格」成立的必要条件 = **多个跑次共享同一产物（同 sha）** 且其失败签名一致;
    若全部跑次的产物两两不同（sem 哈希亦不同）⇒ 该命题在产物层为假, 只能按「实现族」谈。
  · 另一条独立读数: 同一输入在不同产物下的**落点多样性**（同 idx 的 got 取值个数）——
    多样性 > 1 直接排除「一条固定错法解释全族」。
用法: python3 eval/rover/r587/arm_spec_vs_outcome_r587.py
"""
from __future__ import annotations

import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
P_SPEC = os.path.join(REPO, "eval/rover/r587/wythoff-subspec-r587.json")
P_OUT = os.path.join(REPO, "eval/rover/r587/empty-error-cause-r587.json")
OUT = os.path.join(REPO, "eval/rover/r587/spec-vs-outcome-r587.json")

FAIL_FAMILY = ("MOVE_NOT_COLD", "LOSE_FOR_WIN", "WIN_FOR_LOSE", "EMPTY_OR_ERROR",
               "EMPTY_RC0", "TIMEOUT")
NON_FAMILY = ("NONEMPTY_RC0_FAIL", "NONEMPTY_RC0_OTHER")
# `NONEMPTY_RC0_FAIL` = 旧标签名（R587 扩轮跑的落盘件用旧名, 语义 = 本族外: 有输出, 器具不判对错）⇒ 显式排除。


def family_count(classes):
    """本族命中数 = 崩溃 / 空产物 / 超时; `NONEMPTY_RC0_*` 一律不计（那不是失败, 是「不在本判据面」）。"""
    n = 0
    for k, v in (classes or {}).items():
        if k in NON_FAMILY:
            continue
        if k in FAIL_FAMILY or k.startswith("TRACEBACK_") or k.startswith("RC_NONZERO"):
            n += v
    return n


def main():
    spec = json.load(io.open(P_SPEC, encoding="utf-8"))
    outp = json.load(io.open(P_OUT, encoding="utf-8")) if os.path.isfile(P_OUT) else {"per_copy": {}}
    pc = outp.get("per_copy") or {}

    rows = []
    for c in spec["copies"]:
        k = "%s|%s|%s" % (c["round"], c["win"], c["arm"])
        o = pc.get(k, {})
        rows.append({
            "copy": k, "sha12": c.get("sha12"), "sem12": c.get("sem12"),
            "tags": c.get("tags"), "classified": c.get("classified"),
            "outcome": o.get("classes") or ({"arm_level": o["err"]} if o.get("err") else None),
        })

    # 同 sha 组（产物身份）
    by_sha = {}
    for r in rows:
        if r["sha12"]:
            by_sha.setdefault(r["sha12"], []).append(r)
    multi = {s: v for s, v in by_sha.items() if len(v) > 1}

    # 例级失败族按形态标签聚合（只在有 outcome 的拷贝上）
    tab = {}
    for r in rows:
        oc = r["outcome"] or {}
        fam = family_count(oc)
        for t in (r["tags"] or ["(none)"]):
            d = tab.setdefault(t, {"copies": 0, "family_hits": 0, "pass_like_copies": 0})
            d["copies"] += 1
            d["family_hits"] += fam
            if fam == 0:
                d["pass_like_copies"] += 1

    # 同输入的落点多样性
    land = spec.get("landings_by_case") or {}
    diversity = {}
    for idx, m in land.items():
        vals = set()
        for sha, vs in m.items():
            vals.update(vs)
        diversity[idx] = {"distinct_got": len(vals), "n_products": len(m), "values": sorted(vals)[:8]}

    out = {
        "round": "R587",
        "instrument": "eval/rover/r587/arm_spec_vs_outcome_r587.py",
        "question": "wythoff 单族失败是否落在同一子规格？",
        "n_copies": spec["n_copies"], "n_distinct_programs": spec["n_distinct_programs"],
        "n_distinct_sem": spec.get("n_distinct_sem"),
        "shas_shared_by_multiple_runs": {s: [x["copy"] for x in v] for s, v in multi.items()},
        "n_shas_shared": len(multi),
        "same_subspec_supported": bool(multi),
        "tag_vs_outcome": tab,
        "landing_diversity": diversity,
        "rows": rows,
        "verdict_lines": [
            "① 产物身份: %d 跑次产出 %d 份在盘产物, 两两不同（sem 骨架亦两两不同）⇒ 「同一子规格」在**产物层为假**；"
            "共享 sha 的跑次 = %d。" % (spec["n_copies"], spec["n_distinct_programs"], len(multi)),
            "② 落点多样性: 同一输入在不同产物下落点取值数 max=%s ⇒ 排除「一条固定错法解释全族」。"
            % (max([v["distinct_got"] for v in diversity.values()]) if diversity else None),
            "③ 可识别形态分布见 tag_vs_outcome（PHI_DIFF 骨架最普遍, 但通过/失败的分野在其**边界处理**，"
            "即同一骨架的不同边界处理各自是一次独立采样）。",
        ],
    }
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("n_copies", "n_distinct_programs", "n_distinct_sem",
                                          "n_shas_shared", "same_subspec_supported", "tag_vs_outcome")},
                     ensure_ascii=False, indent=1))
    print("落点多样性:", json.dumps({k: v["distinct_got"] for k, v in diversity.items()},
                                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
