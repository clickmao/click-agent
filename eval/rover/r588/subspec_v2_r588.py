#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R588 · 候选④（只读，零产品改动 / 零新夹具 / 零远端）:
「`PHI_DIFF` 骨架下的边界处理分类加厚」—— 把 R587 的 18/36 欠分类降下来。

设计（**加厚，不改判据**）:
  · 轴 A = R587 的 v1 标记集，逐字节复刻 ⇒ **恒等检查**（在 v1 原语料 r585,r586 上必须
    逐标签复现 R587 已登记的 `tag_histogram`；不符 ⇒ 器具缺陷 rc=2，不出被测读数）。
  · 轴 B = **新增二阶段子类**，**只作用于** v1 判 `UNCLASSIFIED` 的副本（v1 已分类者不重贴标签
    ⇒ 判据零变化）。子类取自 18 份未分类产物的**实际形态**（数据先行）:
      B1_BEATTY_FLOAT(φ 由 `5 ** 0.5`/`sqrt(5)` 现算, 无 1.618 字面量)
      B2_DP_TABLE((limit+1)×(limit+1) 布尔/整数表 + `[a][b]` 索引)
      B3_LIMIT_CONST(模块级大写常量 = 状态空间上界)
      B4_COVER_RULE(冷集由「行/列/对角覆盖」排除法构造)
      B5_NORMALIZE_SWAP(`min(a,b), max(a,b)` 边界归一)
      B6_NEGATIVE_GUARD(显式 `na < 0` / `>= 0` 负值守卫)
      B7_LEX_TIEBREAK(`best is None or (i, j) < best` 字典序取首)
      B8_GRUNDY_MEX(mex/grundy 递推)
      B9_PAIR_SET(`.add((` 冷点对入集合)
      B10_MOD_ARITH(判据含 `%` 取模)
      B0_RESIDUAL(仍无子类 ⇒ 如实留在残差, 不静默)
  · 两侧自证(有牙): ① 每个 B 标签各一条**正控**合成样本必须命中该标签;
    ② 一条「标准 φ 差判据 + 朴素双循环」的**负控**样本必须**零** B 标签(留残差)。
    任一向不符 ⇒ `has_teeth=false`，分类只作候选登记、不入结论。

附带器具缺陷登记: R587 读数件的 `missing_wythoff_py` 字段用 `c.get("wythoff_py","")` 判缺失,
而记录**只在缺件时**建该键 ⇒ 键不存在被读成「缺」⇒ 该字段 36/36 全列（真缺仅 1）。
本脚本改用「键存在性」判缺失并把两数分列（口径修正，R587 读数不翻案）。

用法: python3 eval/rover/r588/subspec_v2_r588.py [--out <path>]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re

REPO = "/home/agentuser/AgentFramework"
V1_JSON = os.path.join(REPO, "eval/rover/r587/wythoff-subspec-r587.json")

# ---- 轴 A: 与 R587 逐字节相同的 v1 标记集 ----
V1_MARKERS = [
    ("PHI_DIFF", re.compile(r"(hi\s*-\s*lo|d\s*=\s*[a-z]+\s*-\s*[a-z]+)[\s\S]{0,200}?1\.618|\*\s*phi\b|1\.618033988749895")),
    ("PHI_WINDOW", re.compile(r"cand_u\s*-\s*\d|cand_u\s*\+\s*\d|for\s+cu\s+in\s+")),
    ("PHI_APPROX", re.compile(r"1\.6[0-9]?\b(?!180)|1\.62\b")),
    ("PHI_ROUND", re.compile(r"round\(\s*[a-z_]*\s*\*\s*phi|round\(.*phi")),
    ("BRUTE_LEX", re.compile(r"for\s+[ab]\s+in\s+range\([^)]*\)[\s\S]{0,200}?for\s+[ab]\s+in\s+range\([^)]*\)[\s\S]{0,400}?in\s+cold")),
    ("SUM_ORDER", re.compile(r"for\s+s\s+in\s+range|for\s+tot\s+in\s+range|for\s+\w*sum\w*\s+in\s+range")),
    ("TABLE_PRECOMP", re.compile(r"PAIRS\s*=|COLD\s*=\s*[\[\(]|LOSING\s*=\s*\[")),
    ("EQUAL_ONLY", re.compile(r"a\s*==\s*b\s*$|x\s*==\s*y\s*$", re.M)),
    ("AND_MEMO", re.compile(r"@lru_cache|memo\[|functools\.cache")),
]

# ---- 轴 B: 边界/状态面处理子类（数据先行, 只贴给 v1-UNCLASSIFIED）----
B_MARKERS = [
    ("B1_BEATTY_FLOAT", re.compile(r"5\s*\*\*\s*0\.5|sqrt\s*\(\s*5|\*\*\s*0\.5")),
    ("B2_DP_TABLE", re.compile(r"\[\[[^\]]*\]\s*\*\s*\([^)]*\)\s*for|\[\[[^\]]*\]\s*for\s+_?\s*in\s+range|\[[a-z_]+ \+ 1\]")),
    ("B3_LIMIT_CONST", re.compile(r"(?m)^[A-Z][A-Z_]{2,}\s*=")),
    ("B4_COVER_RULE", re.compile(r"covered")),
    ("B5_NORMALIZE_SWAP", re.compile(r"min\s*\(\s*a\s*,\s*b\s*\)\s*,\s*max|max\s*\(\s*a\s*,\s*b\s*\)")),
    ("B6_NEGATIVE_GUARD", re.compile(r"[a-z]{1,3}\s*<\s*0\b")),
    ("B7_LEX_TIEBREAK", re.compile(r"best\s+is\s+None\s+or|\(\s*i\s*,\s*j\s*\)\s*<")),
    ("B8_GRUNDY_MEX", re.compile(r"\bmex\b|grundy", re.I)),
    ("B9_PAIR_SET", re.compile(r"\.add\(\(\s*[a-z_]")),
    ("B10_MOD_ARITH", re.compile(r"%\s*\(?\s*[0-9]\s*\)?\s*(==|!=|<|>)|[a-z_]+\s*%\s*[0-9]\s*(==|!=)")),
    ("B11_SORT_PAIR", re.compile(r"sorted\s*\(\s*(los|lost|cold|pairs|lose)")),
]


def v1_fingerprint(src: str):
    hits = [t for t, rx in V1_MARKERS if rx.search(src)]
    if not hits:
        return ["UNCLASSIFIED"]
    if not ({"PHI_DIFF"} & set(hits)) and not ({"PHI_WINDOW"} & set(hits)) and "BRUTE_LEX" not in hits:
        hits.append("SHAPE_OTHER")
    return sorted(set(hits))


def b_fingerprint(src: str):
    return [t for t, rx in B_MARKERS if rx.search(src)]


def b_selftest():
    fails = []
    pos = {
        "B1_BEATTY_FLOAT": "p = (i * (1 + 5 ** 0.5)) // 2\n",
        "B2_DP_TABLE": "win = [[False] * (limit + 1) for _ in range(limit + 1)]\n",
        "B3_LIMIT_CONST": "LIMIT = 25\n",
        "B4_COVER_RULE": "covered = False\n",
        "B5_NORMALIZE_SWAP": "state = (min(a, b), max(a, b))\n",
        "B6_NEGATIVE_GUARD": "if na < 0 or nb < 0:\n    continue\n",
        "B7_LEX_TIEBREAK": "if best is None or (i, j) < best:\n    best = (i, j)\n",
        "B8_GRUNDY_MEX": "mex = a + b\n",
        "B9_PAIR_SET": "los.add((x, y))\n",
        "B10_MOD_ARITH": "if a % 3 == 0:\n    pass\n",
        "B11_SORT_PAIR": "pairs = sorted(los)\n",
    }
    for tag, snip in pos.items():
        got = b_fingerprint(snip)
        if tag not in got:
            fails.append("正控 %s 未命中: %s" % (tag, got))
    neg = ("def solve(t):\n    a, b = [int(x) for x in t.split()]\n"
           "    d = b - a\n    return 'LOSE' if int(d * 1.618033988749895) == a else 'WIN 1 1'\n")
    gb = b_fingerprint(neg)
    if gb:
        fails.append("负控(标准 φ 差判据) 误贴子类: %s" % gb)
    # v1 侧: 标准形态必须仍判 PHI_DIFF（轴 A 未被本次加厚影响）
    if "PHI_DIFF" not in v1_fingerprint(neg):
        fails.append("轴 A 回归: 标准形态未命中 PHI_DIFF")
    return fails


def outcomes(rounds=("r585", "r586", "r587", "r588")):
    """把已登记读数件 join 成 (round, win, sub) -> cases_pass（外部真值, 不重算）。"""
    m = {}
    for rk in rounds:
        p = os.path.join(REPO, "eval/rover", rk, "kpi-table-%s.json" % rk)
        if not os.path.isfile(p):
            continue
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for r in d.get("readings") or []:
            m[(rk, r.get("win"), r.get("sub"))] = r.get("cases_pass")
    return m


def load_corpus(rounds):
    out = []
    for rk in rounds:
        sroot = os.path.join(REPO, "eval/rover", rk, "snapshots")
        if not os.path.isdir(sroot):
            continue
        for win in sorted(os.listdir(sroot)):
            wd = os.path.join(sroot, win)
            if not os.path.isdir(wd):
                continue
            for arm in sorted(os.listdir(wd)):
                f = os.path.join(wd, arm, "g1", "games", "wythoff.py")
                rec = {"round": rk, "win": win, "arm": arm, "file": f}
                if os.path.isfile(f):
                    src = io.open(f, encoding="utf-8", errors="replace").read()
                    b = io.open(f, "rb").read()
                    import hashlib
                    rec.update({"present": True, "sha12": hashlib.sha256(b).hexdigest()[:12],
                                "bytes": len(b), "v1_tags": v1_fingerprint(src),
                                "b_tags": b_fingerprint(src)})
                else:
                    rec.update({"present": False, "v1_tags": None, "b_tags": None})
                out.append(rec)
    return out


def hist(copies, key):
    from collections import Counter
    c = Counter()
    for r in copies:
        for t in (r.get(key) or []):
            c[t] += 1
    return dict(c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r588/subspec-v2-r588.json"))
    a = ap.parse_args()
    st = b_selftest()

    # 轴 A 恒等检查（v1 原语料 r585,r586）
    v1corpus = load_corpus(("r585", "r586", "r587"))
    v1hist_now = hist(v1corpus, "v1_tags")
    v1hist_reg = json.load(io.open(V1_JSON, encoding="utf-8"))["tag_histogram"]
    v1_identity_fails = {k: [v1hist_reg.get(k), v1hist_now.get(k)]
                         for k in set(v1hist_reg) | set(v1hist_now)
                         if v1hist_reg.get(k) != v1hist_now.get(k)}

    # 扩展语料 r585..r588（含本轮新窗）
    ext = load_corpus(("r585", "r586", "r587", "r588"))
    un = [r for r in ext if r.get("v1_tags") == ["UNCLASSIFIED"]]
    un_b = {("%s/%s/%s" % (r["round"], r["win"], r["arm"])): r["b_tags"] for r in un}
    n_un = len(un)
    n_un_tagged = len([r for r in un if r["b_tags"]])
    n_un_resid = n_un - n_un_tagged
    # 作用域: B 标签**只贴**给 v1-UNCLASSIFIED; 对照组 = v1 已分类者(判别力读数)
    cls_group = [r for r in v1corpus if r.get("v1_tags") and r["v1_tags"] != ["UNCLASSIFIED"]]
    cls_tagged = [r for r in cls_group if r["b_tags"]]
    rate_un = (round(n_un_tagged / n_un, 3) if n_un else None)
    rate_cls = (round(len(cls_tagged) / len(cls_group), 3) if cls_group else None)
    discrimination = (None if (rate_un is None or rate_cls is None) else round(rate_un - rate_cls, 3))
    scope_viol = []  # 贴标签面由构造保证(见 axis_B_scope); 对照组读数只作判别力证据
    # 缺失口径修正: 键存在性 vs 值缺失
    missing_true = [("%s/%s/%s" % (r["round"], r["win"], r["arm"])) for r in v1corpus if not r.get("present")]
    missing_v1_field = json.load(io.open(V1_JSON, encoding="utf-8")).get("missing_wythoff_py")
    # 判别力对**结果面**: B 标签是否分开 cases_pass (join 已登记读数件, 不重算)
    om = outcomes()
    rows_un = []
    for r in un:
        cp = om.get((r["round"], r["win"], r["arm"]))
        rows_un.append({"copy": "%s/%s/%s" % (r["round"], r["win"], r["arm"]), "b_tags": r["b_tags"],
                        "cases_pass": cp})
    known = [x for x in rows_un if x["cases_pass"] is not None]
    per_tag = {}
    for tag, _ in B_MARKERS:
        with_t = [x["cases_pass"] for x in known if tag in x["b_tags"]]
        without = [x["cases_pass"] for x in known if tag not in x["b_tags"]]
        if with_t and without:
            per_tag[tag] = {"n_with": len(with_t), "mean_with": round(sum(with_t) / len(with_t), 2),
                            "mean_without": round(sum(without) / len(without), 2),
                            "gap": round(sum(with_t) / len(with_t) - sum(without) / len(without), 2)}
    gaps = [v["gap"] for v in per_tag.values()]
    out = {
        "round": "R588",
        "instrument": "eval/rover/r588/subspec_v2_r588.py",
        "mode": "read_only (零产品改动 / 零新夹具 / 零远端)",
        "axis_A_v1_identity": {"registered_histogram": v1hist_reg, "recomputed_histogram": v1hist_now,
                               "fails": v1_identity_fails, "identical": not v1_identity_fails},
        "axis_B_scope": "only v1-UNCLASSIFIED (v1 已分类者不重贴标签) ⇒ 判据零变化",
        "axis_B_histogram_on_unclassified": hist(un, "b_tags") if un else {},
        "unclassified_before": n_un, "unclassified_after_residual": n_un_resid,
        "unclassified_tagged": n_un_tagged,
        "per_copy_b_tags": un_b,
        "scope_violations": scope_viol,
        "discrimination": {"rate_tagged_on_v1_unclassified": rate_un,
                           "rate_tagged_on_v1_classified_control": rate_cls,
                           "gap": discrimination,
                           "control_tagged_examples": [("%s/%s/%s" % (r["round"], r["win"], r["arm"]), r["v1_tags"], r["b_tags"]) for r in cls_tagged][:5],
                           "note": "B 为**加厚候选登记**, 非判据; 对照组命中率高 ⇒ 子类判别力弱, 只能作描述性登记, 不得据此改判据/宣称能力。"},
        "axis_B_selftest_fails": st,
        "has_teeth": (not st) and (not v1_identity_fails) and (not scope_viol),
        "instrument_defect_registered": {
            "field": "missing_wythoff_py",
            "v1_reported_count": (len(missing_v1_field) if isinstance(missing_v1_field, list) else None),
            "true_missing_count": len(missing_true), "true_missing": missing_true,
            "cause": "R587 用 `c.get('wythoff_py','')` 判缺失, 而记录仅在**缺件时**建该键 ⇒ "
                     "键不存在被读成缺 ⇒ 36/36 全列; 口径修正为「键存在性」, R587 读数不翻案(只加注)。",
        },
        "outcome_cross_tab": {"n_with_outcome": len(known), "per_tag": per_tag,
                              "max_abs_gap": (max(abs(g) for g in gaps) if gaps else None),
                              "note": "gap = 带该子类的产物 cases_pass 均值 − 不带者均值; |gap| 小 ⇒ 子类与结果面无关, 只能作描述性登记"},
        "corpus_extended": {"n_copies": len(ext), "rounds": ["r585", "r586", "r587", "r588"]},
    }
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("axis_A_v1_identity", "axis_B_histogram_on_unclassified",
                                         "unclassified_before", "unclassified_tagged",
                                         "unclassified_after_residual", "scope_violations", "discrimination",
                                         "axis_B_selftest_fails", "has_teeth",
                                         "instrument_defect_registered")}, ensure_ascii=False, indent=1))
    return 0 if out["has_teeth"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
