#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R629 · 候选④ 负控指标形态转正：**禁用 `agreement(臂, 产品)` 形态作负控门**。

R627 预注册判据 ③ 的实测结论（逐字）：旧形态 `agreement ≤ 0.25` **已判定为无牙**——实测
`N2 = 0.8333 ≫ 0.25`（该形态度量为「独立 oracle 与产品在**同形口径**下的一致性」，同形时
天花板本就近 1；三档负控 0.8750 / 0.8333 / 0.7583 全部挤在 **[0.75, 0.88]** 窄带内），
⇒ 以它为门的负控**恒过**。正确形态 = **臂间差异量**（`symdiff_hits_vs_产品` 与 `hits_delta`，
实测 `POS=0` / `N1=15` / `N2=20` / `N3=29` 单调可辨）。

本器具把「形态转正」做成**机检 + 成对控制**，并**不翻案** R627 的 FAIL 读数：
  K1  差异量形态存在、且**单调可辨**（symdiff 严格递增 ∧ hits_delta 严格递减）
  K2  正控逐例复现（POS 的 symdiff == 0 ∧ delta == 0）
  K3  **禁用旧形态**：新判据集合里不得出现 `agreement(臂, 产品)` 作门
  K4  旧形态的**无牙性**原样留档（N2 = 0.8333 ≫ 0.25 ⇒ 若旧形态仍在门上，判红）

成对控制（`--controls`）：
  NEG-A  注入一条「旧形态作门」的判据 ⇒ 必须判红（证明 K3 有牙，非恒绿）
  NEG-B  把差异量**清单平化**（三档同值）⇒ 必须判红（证明 K1 有牙，非恒绿）
  POS-B  真盘差异量 ⇒ 判绿

只读、零产品源码改动、零远端 LLM。
退出码：0 = 形态已转正（差异量形态有牙 ∧ 旧形态已离门）；1 = 差异量形态无牙；
        2 = 器具缺陷（旧形态仍在门上 / 读数不可读）；3 = 输入缺失。
"""

import argparse
import hashlib
import io
import json
import os
import sys

BAN_OLD_FORM = "agreement(臂, 产品)"
OLD_GATE_FORM = "agreement ≤ 0.25"
BAN_OLD_FORM_ASCII = "agreement(arm,product)"


def _repo_root(start):
    p = os.path.abspath(start)
    while p != "/":
        if os.path.isdir(os.path.join(p, "eval", "rover")) and os.path.isdir(os.path.join(p, "src")):
            return p
        p = os.path.dirname(p)
    return os.path.abspath(os.path.join(start, ".."))


REPO = _repo_root(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(REPO, "eval/capability/baselines.json")
SRC = os.path.join(REPO, "eval/rover/r627/oracle-r627.json")
PREREG = os.path.join(REPO, "eval/rover/r627/prereg-r627.json")


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


def sha12(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12] if os.path.exists(p) else None


def entry(d, eid):
    for x in d["entries"]:
        if x["id"] == eid:
            return x
    return None


def gate_scan(text, extra_forms=()):
    """K3：判据集合里若把旧形态挂上门（或显式出现禁用形态）⇒ 返回命中项。"""
    hits = []
    blob = text
    for f in (BAN_OLD_FORM, OLD_GATE_FORM, BAN_OLD_FORM_ASCII) + tuple(extra_forms):
        if f and f in blob:
            hits.append(f)
    return hits


def monotone_ok(sym, delta):
    vs = [sym[k] for k in ("POS", "N1", "N2", "N3")]
    vd = [delta[k] for k in ("POS", "N1", "N2", "N3")]
    inc = all(vs[i] < vs[i + 1] for i in range(len(vs) - 1))
    dec = all(vd[i] > vd[i + 1] for i in range(len(vd) - 1))
    return bool(inc and dec), {"symdiff_seq": vs, "hits_delta_seq": vd,
                               "symdiff_strict_inc": inc, "delta_strict_dec": dec}


def new_gate_texts(prereg):
    """K3 的**作用域**（三处，逐条机读，不扫散文）：
      ① 预注册机读字段 `nc_metric_form.gate_forms`（本轮**新门**形态清单）；
      ② 预注册 `criteria` 文本（本轮判据集合）；
      ③ 其余一律**不在作用域**：历史基准记录的 `threshold` 留档文本**必须**逐字引用旧形态
         （R627 实测「agreement ≤ 0.25 无牙」）⇒ 把它算进门即**自指假红**（技能「自指实例必入档」）；
         本器具自身用于**声明禁用**的常量（`OLD_GATE_FORM` 等）同样不入门扫描（否则判据自指自身）。"""
    texts = []
    if prereg:
        texts.append(json.dumps((prereg.get("nc_metric_form") or {}).get("gate_forms", []),
                                ensure_ascii=False))
        texts.append(json.dumps(prereg.get("criteria", {}), ensure_ascii=False))
    return texts


def assess(base, src, prereg, injected_criterion=None):
    e = entry(base, "rerank-oracle-form")
    v = (e or {}).get("value") or {}
    sym = v.get("symdiff_hits_vs_product") or {}
    dl = v.get("hits_delta_vs_product") or {}
    agr = ((src.get("readings") or {}).get("agreement_vs_product_B10") or {})
    mon, mon_ev = monotone_ok(sym, dl) if (len(sym) == 4 and len(dl) == 4) else (False, {})
    old_toothless = bool(agr) and max(agr.values()) - min(agr.values()) < 0.5
    # 旧形态「无牙」的读数证据：最低档也远高于旧门阈
    old_min = min(agr.values()) if agr else None
    crit_text = "\n".join(new_gate_texts(prereg))
    if injected_criterion:      # 负控：把一条**旧形态作门**的判据注入本轮门清单
        crit_text += "\n" + injected_criterion
    banned = gate_scan(crit_text)
    recorded_history = {"quotes_old_form": bool(
        "agreement" in json.dumps((e or {}).get("threshold", ""), ensure_ascii=False)),
        "role": "留档（R627 实测旧形态无牙）—— 不参与 K3 扫描作用域，禁作门"}
    res = {
        "old_form_on_gate": bool(banned),
        "banned_hits": banned,
        "old_form_reading_min": old_min,
        "old_form_spread": (max(agr.values()) - min(agr.values())) if agr else None,
        "old_form_toothless": old_toothless,
        "recorded_history": recorded_history,
        "gate_scan_scope": "本轮新判据集合（prereg criteria + 器具 gate 行），不含历史留档文本",
        "diff_form_monotone": mon,
        "diff_form_evidence": mon_ev,
        "pos_reproduces_exactly": bool(sym.get("POS") == 0 and dl.get("POS") == 0),
        "single_arm_not_better_than_pos": bool(sym.get("N1", -1) >= sym.get("POS", 0)),
        "defects": [],
    }
    if res["old_form_on_gate"]:
        res["defects"].append({"id": "E1", "what": "禁用形态仍在门上", "hits": banned})
    if not mon:
        res["defects"].append({"id": "E2", "what": "差异量形态无牙（非单调或不可辨）", "ev": mon_ev})
    if not res["pos_reproduces_exactly"]:
        res["defects"].append({"id": "E3", "what": "正控未逐例复现"})
    res["rc"] = 2 if (res["defects"] and any(d["id"] == "E1" for d in res["defects"])) else (
        1 if res["defects"] else 0)
    res["judge"] = ("形态已转正（差异量单调可辨 ∧ 旧形态离门；旧形态无牙读数原样留档）"
                    if res["rc"] == 0 else
                    ("器具缺陷（旧形态仍在门上）" if res["rc"] == 2 else "负控形态无牙"))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--controls", action="store_true")
    a = ap.parse_args()
    miss = [p for p in (BASE, SRC) if not os.path.exists(p)]
    if miss:
        print("INPUT_MISSING %s" % miss)
        return 3
    base, src = load(BASE), load(SRC)
    prereg = load(PREREG) if os.path.exists(PREREG) else None
    pos = assess(base, src, prereg, injected_criterion=None)
    out = {
        "schema": "r629-nc-metric-form/1", "round": "R629", "candidate": "④ 负控指标形态转正",
        "baseline_ref": "eval/capability/baselines.json#rerank-oracle-form",
        "baseline_source_sha12": sha12(SRC),
        "rule": "负控门只许用**臂间差异量**；`agreement(臂, 产品)` 形态禁用（R627 实测无牙：N2=0.8333 ≫ 0.25）",
        "POS_readings": pos,
    }
    if a.controls:
        negA = assess(base, src, prereg, injected_criterion="负控门：agreement(臂, 产品) ≤ 0.25")
        flat = json.loads(json.dumps(base))
        e = entry(flat, "rerank-oracle-form")
        e["value"]["symdiff_hits_vs_product"] = {k: 0 for k in ("POS", "N1", "N2", "N3")}
        e["value"]["hits_delta_vs_product"] = {k: 0 for k in ("POS", "N1", "N2", "N3")}
        negB = assess(flat, src, prereg)
        paired: dict = {
            "NEG_A_old_form_on_gate": {"old_form_on_gate": negA["old_form_on_gate"],
                                       "defect_ids": [d["id"] for d in negA["defects"]], "rc": negA["rc"]},
            "NEG_B_flat_diff_form": {"diff_form_monotone": negB["diff_form_monotone"],
                                     "defect_ids": [d["id"] for d in negB["defects"]], "rc": negB["rc"]},
            "POS_B_true_readings": {"rc": pos["rc"], "monotone": pos["diff_form_monotone"]},
        }
        paired["teeth"] = bool(
            (not pos["old_form_on_gate"])
            and negA["old_form_on_gate"] and ("E1" in [d["id"] for d in negA["defects"]])
            and (not negB["diff_form_monotone"]) and ("E2" in [d["id"] for d in negB["defects"]])
            and pos["diff_form_monotone"])
        out["paired_controls"] = paired
    out["verdict"] = {"rc": pos["rc"], "judge": pos["judge"]}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("旧形态在门上      : %s（命中 %s）" % (pos["old_form_on_gate"], pos["banned_hits"] or "-"))
    print("旧形态无牙读数    : min=%.4f spread=%.4f（旧门阈 0.25）"
          % (pos["old_form_reading_min"] or -1, pos["old_form_spread"] or -1))
    print("差异量单调可辨    : %s %s" % (pos["diff_form_monotone"], pos["diff_form_evidence"]))
    print("正控逐例复现      : %s" % pos["pos_reproduces_exactly"])
    if a.controls:
        print("成对控制          : %s" % json.dumps(out["paired_controls"], ensure_ascii=False))
    print("rc=%d（%s）" % (out["verdict"]["rc"], out["verdict"]["judge"]))
    return out["verdict"]["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
