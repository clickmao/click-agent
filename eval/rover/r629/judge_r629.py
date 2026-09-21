#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R629 · 候选① 判决面：**判决来源机检 + 铁律 11 指针同源派生 + 声明件存在性 fail-closed**。

R628 自捕缺陷 ①（判决面 ≠ 预注册主判据面）+ 本轮新增两件（见 evidence/instrument-defects-r629.json）：
  D1  记录判决 `rc=1` 的 `verdict.blocked` 唯一项为 `C1_quality_paired:R628D`，而预注册
      `criteria` 声明的主判据是 **C7（判据 v3 第五窗集）**，且 `pool_taskface_r628.py` 的 C1 自述
      「仅作同向参照、不出判决」⇒ **判决来源 ≠ 主判据**，而 `verdict-r628.json` 顶层**无 C7 键**。
  D2  `verdict.iron11` 为**硬编码字符串** `eval/rover/r507pre/precondition-r628.json`（该路径不存在），
      真实前置器输出落在 `run_r628.sh` 的 `$D/precond-r628.json` ⇒ 指针与 `--out` **不同源**。
  D3  预注册 `declared_scope` / `precond.scope_require` 声明的轮级件
      `eval/rover/r628/taskface-pool-r628.json` **从未写出**，而 `precond.declared_absent` 为 `[]`
      ⇒ 声明件缺失**未登记**（`exec_precondition.py` 的存在性检查只覆盖 `<win>/<arm>` 形态的项）。

本器具三件事都做成**无条件计算 + fail-closed**（缺键写 `None`，不只走分支）：
  K1  主判据键存在性 + `verdict_source`（== 主判据名才算判决面成立）
  K2  `iron11` 指针与 `--out` 同源派生 + 存在性（缺失**出声**，不静默）
  K3  声明件存在性清单（缺件 ⇒ fail-closed 记器具缺陷）

成对控制（`--controls`）：
  POS  现盘 R628 verdict        ⇒ `primary_present=false` ∧ 判决源 ≠ 主判据 ⇒ 判「器具缺陷」
  NEG  注入 C7 键的副本          ⇒ `primary_present=true` ∧ `verdict_source=="C7"` ⇒ 判「判决面成立」
  NEG2 `--out` 指向无 precond 的目录 ⇒ `iron11_exists=false` 且**不静默**

退出码：0 = 判决面成立（主判据落盘且判决源 == 主判据）；1 = 主判据判「缺口成立/未过」；
        2 = 器具缺陷（判决面不成立/指针失效/声明件缺失）；3 = 输入缺失。
"""

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile


def _repo_root(start):
    p = os.path.abspath(start)
    while p != "/":
        if os.path.isdir(os.path.join(p, "eval", "rover")) and os.path.isdir(os.path.join(p, "src")):
            return p
        p = os.path.dirname(p)
    raise SystemExit("INPUT_MISSING repo root")


REPO = _repo_root(os.path.dirname(os.path.abspath(__file__)))
PREREG_R628 = os.path.join(REPO, "eval/rover/r628/prereg-r628.json")
VERDICT_R628 = os.path.join(REPO, "eval/rover/r628/verdict-r628.json")
PRECOND_R628 = os.path.expanduser("~/.agentframework/harness/runs/r628/precond-r628.json")


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


def sha12(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12] if os.path.exists(p) else None


# ---- K1 主判据键存在性 + 判决来源 --------------------------------------------
def declared_primary(prereg):
    """主判据键名：**优先取机读字段 `primary_criterion_key`**（R628 缺陷根因 =
    主判据只能靠中文字面「主判据」识别 ⇒ 判决面与判据面脱钩）；无机读字段时才退化为字面扫描。"""
    mk = prereg.get("primary_criterion_key")
    if mk:
        return [mk]
    crit = prereg.get("criteria") or prereg.get("axis_criteria_R628") or {}
    hits = []
    for k, v in crit.items():
        if k in ("note", "rule", "rule_v5"):
            continue
        blob = (k + " " + json.dumps(v, ensure_ascii=False))
        if "主判据" in blob:
            hits.append(k)
    return hits


def verdict_source_of(verdict):
    """判决**实际由谁出**：优先取机读字段 `verdict.verdict_source`（显式声明）；
    缺失时退化为从 `verdict.blocked` 项（形如 `<源>:<臂>`）反解 —— 仅作兜底，
    因为「全过时 blocked 为空」会让来源不可读（R629 自捕第二处）。"""
    inner = verdict.get("verdict") or {}
    explicit = inner.get("verdict_source") or verdict.get("verdict_source")
    if explicit:
        return [explicit] if isinstance(explicit, str) else list(explicit)
    blocked = inner.get("blocked") or verdict.get("blocked") or []
    srcs = []
    for b in blocked:
        if not isinstance(b, str):
            continue
        srcs.append(b.split(":", 1)[0] if ":" in b else b)
    return sorted(set(srcs))


def recorded_iron11_string(verdict):
    """记录件里 iron11 字段的**原样值**（用于证明「硬编码 ≠ 同源派生」）。"""
    inner = verdict.get("verdict") or {}
    return inner.get("iron11") or verdict.get("iron11")


def primary_present(verdict, primary_keys):
    """主判据读数是否落在 verdict **顶层**（机器可读面）。"""
    found = [k for k in primary_keys if k in verdict]
    # 亦接受主判据名出现在顶层键的任意前缀命中（如 C7 / C7_negative_control）
    if not found:
        for k in primary_keys:
            base = k.split()[0].split("_")[0]
            found += [kk for kk in verdict if kk.startswith(base)]
    return sorted(set(found))


# ---- K2 铁律 11 指针同源派生 -------------------------------------------------
def iron11_resolve(out_path, round_tag, explicit=None):
    d = os.path.dirname(os.path.abspath(out_path))
    cands = [explicit] if explicit else []
    cands += [os.path.join(d, "precond-%s.json" % round_tag),
              os.path.join(d, "precondition-%s.json" % round_tag)]
    for p in cands:
        if p and os.path.exists(p):
            return {"pointer": p, "derived_from": "--out", "exists": True,
                    "candidates_checked": cands}
    return {"pointer": None, "derived_from": "--out", "exists": False,
            "candidates_checked": cands,
            "note": "指针缺失 ⇒ 出声记 null（禁回退到硬编码历史路径）"}


# ---- K3 声明件存在性（fail-closed）------------------------------------------
def declared_missing(prereg, precond, verdict=None):
    """返回**未登记**的缺失声明件（已登记在 `declared_absent` 者不算缺陷）。"""
    registered = set((prereg.get("declared_absent") or [])
                     + ((verdict or {}).get("declared_absent") or []))
    declared = list(prereg.get("declared_scope") or [])
    declared += [s for s in ((precond or {}).get("scope_require") or [])
                 if not str(s).startswith(tuple("%s/" % w for w in ["w1", "w2", "w3"]))]
    miss = []
    for rel in sorted(set(declared)):
        p = rel if os.path.isabs(rel) else os.path.join(REPO, rel)
        if not os.path.exists(p) and rel not in registered:
            miss.append(rel)
    return miss


def judge(prereg, verdict, precond, out_path, round_tag, iron11_src=None):
    pk = declared_primary(prereg) or declared_primary(verdict)
    present = primary_present(verdict, pk)
    vsrc = verdict_source_of(verdict)
    primary_name = "C7" if any(k.startswith("C7") for k in pk) else (pk[0] if pk else None)
    src_is_primary = bool(primary_name) and any(s.startswith(primary_name) for s in vsrc)
    ir = iron11_resolve(out_path, round_tag, iron11_src)
    # 记录件里的指针**本身**也要查：R628 记录的是硬编码历史路径（不存在）且与 --out 不同源
    rec = recorded_iron11_string(verdict)
    rec_abs = None
    if isinstance(rec, str) and rec:
        rec_abs = rec if os.path.isabs(rec) else os.path.join(REPO, rec)
    ir["recorded_pointer"] = rec
    ir["recorded_pointer_exists"] = bool(rec_abs and os.path.exists(rec_abs))
    ir["recorded_pointer_matches_derived"] = bool(ir["pointer"] and rec_abs
                                                  and os.path.abspath(rec_abs) == os.path.abspath(ir["pointer"]))
    miss = declared_missing(prereg, precond, verdict)
    # 无条件计算：每个字段在任何分支下都有取值
    res = {
        "primary_declared_keys": pk,
        "primary_name": primary_name,
        "primary_present_in_verdict_toplevel": present,
        "recorded_verdict_source": vsrc,
        "recorded_verdict_source_raw": ((verdict.get("verdict") or {}).get("blocked")),
        "recorded_iron11_string": recorded_iron11_string(verdict),
        "verdict_source_is_primary": src_is_primary,
        "recorded_rc": (verdict.get("verdict") or {}).get("rc"),
        "iron11": ir,
        "declared_artifacts_missing": miss,
        "defects": [],
    }
    if not present:
        res["defects"].append({"id": "D1", "what": "主判据键未落盘进 verdict 顶层",
                               "consequence": "判决面 ≠ 预注册主判据面"})
    if not src_is_primary:
        res["defects"].append({"id": "D1b", "what": "记录判决的来源 ≠ 主判据",
                               "recorded_source": vsrc, "declared_primary": primary_name})
    if not ir["exists"]:
        res["defects"].append({"id": "D2", "what": "铁律 11 指针不可达（与 --out 不同源）",
                               "candidates": ir["candidates_checked"]})
    if not ir["recorded_pointer_exists"]:
        res["defects"].append({"id": "D2b", "what": "记录件里的 iron11 指针指向不存在的路径",
                               "recorded_pointer": rec})
    elif not ir["recorded_pointer_matches_derived"]:
        res["defects"].append({"id": "D2c", "what": "记录指针与 --out 同源派生结果不一致（硬编码）",
                               "recorded_pointer": rec, "derived": ir["pointer"]})
    if miss:
        res["defects"].append({"id": "D3", "what": "声明件缺失未登记",
                               "missing": miss})
    res["rc"] = 2 if res["defects"] else 0
    res["judge"] = "器具缺陷（判决面/指针/声明件）" if res["defects"] else "判决面成立"
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--round-tag", default="r628")
    ap.add_argument("--iron11-src", default=None)
    ap.add_argument("--prereg", default=PREREG_R628)
    ap.add_argument("--verdict", default=VERDICT_R628)
    ap.add_argument("--precond", default=None)
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--nc-out", default=None, help="成对控制读数落盘路径")
    a = ap.parse_args()

    PREREG, VERDICT = a.prereg, a.verdict
    PRECOND = a.precond or (os.path.expanduser("~/.agentframework/harness/runs/%s/precond-%s.json"
                                               % (a.round_tag, a.round_tag)))
    missing = [p for p in (PREREG, VERDICT) if not os.path.exists(p)]
    if missing:
        print("INPUT_MISSING %s" % missing)
        return 3

    prereg, verdict = load(PREREG), load(VERDICT)
    precond = load(PRECOND) if os.path.exists(PRECOND) else None
    prereg_rel = os.path.relpath(PREREG, REPO)

    out = {"schema": "r629-verdict-face/1", "round": "R629", "round_judged": a.round_tag,
           "instrument": {"path": "eval/rover/r629/judge_r629.py",
                          "sha12": sha12(__file__)},
           "inputs": {"prereg": prereg_rel, "prereg_sha12": sha12(PREREG),
                      "verdict": os.path.relpath(VERDICT, REPO), "verdict_sha12": sha12(VERDICT),
                      "precond": os.path.relpath(PRECOND, os.path.expanduser("~")) if os.path.exists(PRECOND) else None,
                      "precond_sha12": sha12(PRECOND)},
           "rule": "主判据键缺失 ⇒ fail-closed rc=2（禁把参照面当判决面）；指针缺失 ⇒ 出声记 null；声明件缺失 ⇒ fail-closed",
           "POS_recorded": judge(prereg, verdict, precond, a.out, a.round_tag, a.iron11_src)}

    controls: dict = {}
    if a.controls:
        tmp = tempfile.mkdtemp(prefix="r629judge_")
        # NEG-A: **正确形态副本** —— 主判据读数落进顶层 ∧ `blocked` 的来源键 == 主判据
        #        （证明机检器对「形式正确」判绿，不只对坏形态判红）
        v2 = json.loads(json.dumps(verdict))
        v2["C7_judge_v3_primary"] = {"median_D_task": -0.66665, "valid_windows": 2,
                                     "threshold_median": -0.34, "pass": True}
        v2["verdict"]["blocked"] = ["C7_judge_v3_primary:R628D"]
        v2p = os.path.join(tmp, "verdict-r628-corrected-form.json")
        io.open(v2p, "w", encoding="utf-8").write(json.dumps(v2, ensure_ascii=False, indent=1))
        neg = judge(prereg, load(v2p), precond, a.out, a.round_tag, a.iron11_src)
        # NEG-B: 指针**不存在**（--out 落在无 precond 的目录）
        empty = os.path.join(tmp, "noprecond")
        os.makedirs(empty, exist_ok=True)
        neg2 = judge(prereg, verdict, precond, os.path.join(empty, "verdict-r629.json"),
                     a.round_tag, a.iron11_src)
        # POS-B: 指针**存在**（--out 落在含 precond 的目录）⇒ D2 必须消失（成对，防「D2 恒真门」）
        withpre = os.path.join(tmp, "withprecond")
        os.makedirs(withpre, exist_ok=True)
        shutil.copy(PRECOND, os.path.join(withpre, "precond-%s.json" % a.round_tag))
        posb = judge(prereg, verdict, precond, os.path.join(withpre, "verdict-r629.json"),
                     a.round_tag, a.iron11_src)
        controls = {
            "NEG_A_corrected_form": {
                "primary_present": bool(neg["primary_present_in_verdict_toplevel"]),
                "verdict_source_is_primary": neg["verdict_source_is_primary"],
                "defect_ids": [d["id"] for d in neg["defects"]]},
            "NEG_B_pointer_missing": {"iron11_exists": neg2["iron11"]["exists"],
                                      "defect_ids": [d["id"] for d in neg2["defects"]]},
            "POS_B_pointer_present": {"iron11_exists": posb["iron11"]["exists"],
                                      "defect_ids": [d["id"] for d in posb["defects"]]},
        }
        controls["teeth"] = bool(
            (not out["POS_recorded"]["primary_present_in_verdict_toplevel"])
            and (not out["POS_recorded"]["verdict_source_is_primary"])
            and neg["primary_present_in_verdict_toplevel"]
            and neg["verdict_source_is_primary"]
            and ("D1" not in [d["id"] for d in neg["defects"]])
            and (not neg2["iron11"]["exists"]) and ("D2" in [d["id"] for d in neg2["defects"]])
            and posb["iron11"]["exists"] and ("D2" not in [d["id"] for d in posb["defects"]]))
        controls["rule"] = ("成对四面：POS(现盘) 判红 D1/D1b/D2/D3 ∧ NEG-A(正确形态副本) 判绿 D1 ∧ "
                            "NEG-B(指针缺失) 判红 D2 ∧ POS-B(指针存在) D2 消失 ⇒ 非恒真门")
        out["paired_controls"] = controls
        shutil.rmtree(tmp, ignore_errors=True)

    out["verdict"] = {
        "rc": out["POS_recorded"]["rc"],
        "judge": out["POS_recorded"]["judge"],
        "note": "rc=2 表**器具缺陷**（R628 记录判决的来源不可信）⇒ 主判据已由 R629 参数化池化器补齐，"
                "见 primary-pool-r629.json（`set5_primary_criterion.C1_primary`）",
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    if a.nc_out:
        os.makedirs(os.path.dirname(os.path.abspath(a.nc_out)), exist_ok=True)
        io.open(a.nc_out, "w", encoding="utf-8").write(json.dumps(
            {"schema": "r629-instrument-defects/1", "round": "R629",
             "defects": out["POS_recorded"]["defects"],
             "teeth": (out.get("paired_controls") or {}).get("teeth"),
             "paired_controls": out.get("paired_controls"),
             "positive_control_on_disk_verdict": {
                 "primary_declared_keys": out["POS_recorded"]["primary_declared_keys"],
                 "primary_present_in_verdict_toplevel": out["POS_recorded"]["primary_present_in_verdict_toplevel"],
                 "recorded_verdict_source": out["POS_recorded"]["recorded_verdict_source"],
                 "verdict_source_is_primary": out["POS_recorded"]["verdict_source_is_primary"],
                 "iron11": out["POS_recorded"]["iron11"],
                 "declared_artifacts_missing": out["POS_recorded"]["declared_artifacts_missing"]},
             "rule": "正控 = 现盘 R628 判据件（须判红：判决面不成立）；负控 = 注入 C7 键副本 / 无 precond 目录（须判绿/出声）"},
            ensure_ascii=False, indent=1))
    p = out["POS_recorded"]
    print("主判据声明键      : %s" % p["primary_declared_keys"])
    print("主判据键落盘      : %s" % p["primary_present_in_verdict_toplevel"])
    print("记录判决来源      : %s（== 主判据: %s）" % (p["recorded_verdict_source"], p["verdict_source_is_primary"]))
    print("铁律11 指针       : exists=%s pointer=%s" % (p["iron11"]["exists"], p["iron11"]["pointer"]))
    print("声明件缺失        : %s" % (p["declared_artifacts_missing"] or "-"))
    if a.controls:
        print("成对控制          : %s" % json.dumps(controls, ensure_ascii=False))
    print("rc=%d（%s）" % (out["verdict"]["rc"], out["verdict"]["judge"]))
    return out["verdict"]["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
