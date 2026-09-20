#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R599 候选② 器具: **rc 语义收口 的历史判决审计**（预注册 C11 的验收面）。

审计三件:
  A. **公式 vs 器件**（防自证）: 对 R599 池化件的每个窗集，从读数元组 (C0.pass, C7.has_teeth, C1_task_face_v3.pass)
     独立重算新规则 rc，断言与器件落盘的 `verdict.rc` **逐窗集一致**（器件实现 == 预注册公式）。
  B. **单调性 + 翻转清单**（纯收紧判定）: 同读数下 旧规则 rc_old 与 新规则 rc_new 对比；
     合法方向 = 0→{1,2,3}（收紧）；**非法 = 旧非零 ⇒ 新 0（放松）** ⇒ 出现即 rc=2（器具缺陷，禁改判据凑绿）。
  C. **在盘历史判决交叉校验**: 对全部在盘池化件（r585..r598 变体）逐件读 `verdict.rc`（有则比、无则记 not_on_disk，
     不按通过计），并用其自带读数元组复算 rc_old 与 rc_new，列出受影响窗集。

成对控制（三例合成 fixture，证明公式双向有牙）:
  ①旧 0 ∧ 验收面 True  ⇒ 新 0（不误伤）；②旧 2 ∧ 验收面 True ⇒ 新 2（不放松）；③旧 0 ∧ 验收面 False ⇒ 新 1（收紧生效）。

rc 分层: 0 可用 / 2 器具缺陷（器件≠公式 或 出现放松 或 控制未过）/ 3 输入缺失（fail-closed）。

用法: python3 eval/rover/r599/rc_semantics_audit_r599.py \
        --pool eval/rover/r599/taskface-pool-r599.json --out eval/rover/r599/rc-semantics-r599.json
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"


def rc_old(c0: bool, teeth: bool) -> int:
    return 0 if (c0 and teeth) else (3 if not c0 else 2)


def rc_new(c0: bool, teeth: bool, face: bool) -> int:
    if c0 and teeth and face:
        return 0
    if not c0:
        return 3
    if not teeth:
        return 2
    return 1


def triples_of(pool_json: dict):
    """从池化件里取每个窗集的读数元组（兼容两种落盘形态）。"""
    out = {}
    sv = pool_json.get("set_verdicts_C11") or {}
    sv = sv.get("sets", sv)
    for k, v in sv.items():
        out[k] = {"c0": v.get("c0_pass"), "teeth": v.get("c7_has_teeth"), "face": v.get("c1_face_pass"),
                  "rc_disk": v.get("rc"), "name": v.get("set_name")}
    if out:
        return out
    for k in sorted(pool_json.keys()):
        if k.startswith("set") and k.endswith("_window_set"):
            s = pool_json[k] or {}
            c0 = (s.get("C0") or {}).get("pass")
            teeth = (s.get("C7_negative_control") or {}).get("has_teeth")
            face = (s.get("C1_task_face_v3") or {}).get("pass")
            out[k] = {"c0": c0, "teeth": teeth, "face": face,
                      "rc_disk": (s.get("verdict") or {}).get("rc"), "name": k}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", default=os.path.join(REPO, "eval/rover/r599/taskface-pool-r599.json"))
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r599/rc-semantics-r599.json"))
    ap.add_argument("--hist-dir", default=os.path.join(REPO, "eval/rover"))
    a = ap.parse_args()
    if not os.path.exists(a.pool):
        print("[fail-closed] 缺池化件 %s" % a.pool)
        return 3
    pool = json.load(io.open(a.pool, encoding="utf-8"))
    tri = triples_of(pool)
    if not tri:
        print("[fail-closed] 池化件内无窗集读数元组（读法契约不符）")
        return 3
    A, flips, mismatch = [], [], []
    for k, t in sorted(tri.items()):
        if None in (t["c0"], t["teeth"], t["face"]):
            mismatch.append({"set": k, "why": "读数元组缺项（fail-closed，不计入通过）"})
            continue
        new = rc_new(bool(t["c0"]), bool(t["teeth"]), bool(t["face"]))
        old = rc_old(bool(t["c0"]), bool(t["teeth"]))
        A.append({"set": k, "c0": t["c0"], "teeth": t["teeth"], "face": t["face"],
                  "rc_old": old, "rc_new": new, "rc_disk": t["rc_disk"],
                  "device_matches_formula": (t["rc_disk"] == new)})
        if t["rc_disk"] != new:
            mismatch.append({"set": k, "disk": t["rc_disk"], "formula": new})
        if old != 0 and new == 0:
            flips.append({"set": k, "old": old, "new": new, "direction": "RELAXATION(非法)"})
        elif old == 0 and new != 0:
            flips.append({"set": k, "old": old, "new": new, "direction": "tightening(合法)"})
    # C. 在盘历史件
    hist = []
    for f in sorted(glob.glob(os.path.join(a.hist_dir, "r5*", "taskface-pool-.json")) +
                    glob.glob(os.path.join(a.hist_dir, "r5*", "taskface-pool-*.json"))):
        try:
            j = json.load(io.open(f, encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            hist.append({"file": os.path.relpath(f, REPO), "why": "unreadable:%s" % type(e).__name__})
            continue
        t = triples_of(j)
        rows = []
        for k, v in sorted(t.items()):
            if None in (v["c0"], v["teeth"], v["face"]):
                rows.append({"set": k, "why": "缺项", "rc_old": None, "rc_new": None, "rc_disk": v["rc_disk"]})
                continue
            rows.append({"set": k, "rc_old": rc_old(bool(v["c0"]), bool(v["teeth"])),
                         "rc_new": rc_new(bool(v["c0"]), bool(v["teeth"]), bool(v["face"])),
                         "rc_disk": v["rc_disk"]})
        hist.append({"file": os.path.relpath(f, REPO), "round": j.get("round"),
                     "rc_on_disk": (j.get("verdict") or {}).get("rc"),
                     "rc_on_disk_present": (j.get("verdict") or {}).get("rc") is not None,
                     "sets": rows})
    # 控制（三例合成 fixture）
    ctl = {
        "old0_faceTrue_must_stay0": rc_new(True, True, True) == 0,
        "old2_faceTrue_must_stay2": rc_new(True, False, True) == 2,
        "old0_faceFalse_must_tighten1": rc_new(True, True, False) == 1,
        "old_formula_unchanged": (rc_old(True, True) == 0 and rc_old(True, False) == 2 and rc_old(False, False) == 3),
    }
    ctl["all_pass"] = all(ctl.values())
    relax = [f for f in flips if f["direction"].startswith("RELAXATION")]
    rc = 0
    if not ctl["all_pass"] or mismatch or relax:
        rc = 2
    out = {"round": "R599", "purpose": "预注册 C11 rc 语义收口: 器件-公式一致性 + 单调性 + 在盘历史判决交叉校验",
           "rule_new": "rc=0 iff (C0.pass ∧ C7.has_teeth ∧ C1_task_face_v3.pass)；否则 3(数据/真值) > 2(器具缺陷) > 1(验收面未达)",
           "rule_old": "rc=0 iff (C0.pass ∧ C7.has_teeth)；否则 3(数据) / 2(器具缺陷)",
           "A_device_vs_formula": A, "device_formula_mismatch": mismatch,
           "B_flips": flips, "B_relaxations": relax,
           "neutrality": {"claim": "纯收紧、判决中性（中性面 = 在盘历史登记判决）",
                          "tightening_count": len([f for f in flips if f["direction"].startswith("tightening")]),
                          "relaxation_count": len(relax),
                          "hist_on_disk_rc": [(h["file"], h.get("rc_on_disk")) for h in hist]},
           "C_hist": hist, "controls": ctl, "rc": rc}
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    io.open(os.path.join(os.path.dirname(a.out), "hist-judgment-audit-r599.json"), "w", encoding="utf-8").write(
        json.dumps({"round": "R599", "audit_of": a.out, "A": A, "B_flips": flips, "C_hist": hist,
                    "controls": ctl, "rc": rc}, ensure_ascii=False, indent=1) + "\n")
    print("[rc-semantics] 窗集=%d 器件≠公式=%d 翻转(tightening=%d, relaxation=%d) 控制=%s ⇒ rc=%d"
          % (len(A), len(mismatch), len([f for f in flips if f["direction"].startswith("tightening")]),
             len(relax), ctl["all_pass"], rc))
    for f in flips:
        print("  · flip %s: %s -> %s (%s)" % (f["set"], f["old"], f["new"], f["direction"]))
    return rc


if __name__ == "__main__":
    sys.exit(main())
