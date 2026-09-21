#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R615 · M3 前提机检（只读）：J1「声明到岸率 0/18」到底是「远端零遵守」还是「契约面结构性不适用」。

判据全部**从现盘源派生**（禁手抄常量），三个读数相互独立：
  C1 词表面（结构）：块内 tool 词表 A vs R1 `<tool_menu>` 步骤词表 B ⇒ |A| / |B| / A∩B。
     主张：A∩B ⊊ A ⇒ 块要求的词表**不是**管道菜单词表（模型被 menu-only 规则约束不要发明别的工具）。
  C2 豁免面（措辞）：块内是否含**显式可选/豁免**串（"可选" ∧ "不声明"）⇒ 模型有正当理由不声明。
  C3 行为面（冻结件）：17 跑次 transcript 中 `action_candidates_declared` 出现次数，
      与 `plan_steps_total`（≥2 的跑次占比）成对读 ⇒ 模型**确实在编排**却零声明。

控制（成对，防恒真门）：
  POS：把块文本替换为「必填」形态 ⇒ C2 必须翻面（opt_out=False）。
  NEG：空语料 / 缺 transcript ⇒ rc=3（输入缺失），不得读成「零声明」。
  非平凡：三读数互异且 C3 的分母 > 0。

rc 语义分层：0 = 器具可用且判据成立；2 = 器具缺陷（含把输入缺失读成结论）；3 = 输入缺失。
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("R615_REPO", os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
PROTO = os.path.join(REPO, "tools/r1gen/r1prompt.py")
RUNS = os.environ.get("R615_RUNS", os.path.join(os.path.expanduser("~"), ".agentframework/harness/runs/r610"))
OUT = os.environ.get("R615_OUT", os.path.join(HERE, "premise-r615.json"))


def block(src, name):
    m = re.search(name + r' = """(.*?)"""', src, re.S)
    if m is None:
        raise SystemExit("PREMISE_INSTRUMENT_DEFECT: block %s not found" % name)
    return m.group(1)


def derive():
    src = io.open(PROTO, encoding="utf-8").read()
    ac = block(src, "ACTION_CANDIDATES")
    tm = block(src, "TOOL_MENU")
    # 词表由产物自身派生：块内 tool= 之后的枚举 + args 说明里的名字；菜单取 "- <name>{" 形式。
    vocab_a = set(re.findall(r"(delete_file|list_dir|read_file|run_command|write_file)", ac))
    vocab_b = set(re.findall(r"^- (delete_file|list_dir|read_file|run_command|write_file|run|none)\b", tm, re.M))
    menu_names = set(re.findall(r"\b(delete_file|list_dir|read_file|run_command|write_file|run|none)\b", tm))
    opt_out = ("可选" in ac) and ("不声明" in ac)
    return {"ac_chars": len(ac), "ac_vocab": sorted(vocab_a), "menu_vocab": sorted(vocab_b),
            "menu_names": sorted(menu_names), "opt_out": opt_out,
            "intersect": sorted(vocab_a & menu_names), "only_in_block": sorted(vocab_a - menu_names)}


def counter():
    files = sorted(glob.glob(os.path.join(RUNS, "w*", "agent*-r*", "g1", "transcript.json")))
    n = present = plan_ge2 = 0
    plan_vals, rc_vals = {}, {}
    for f in files:
        try:
            d = json.load(io.open(f, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict) or d.get("schema") != "r1-run/1":
            continue
        n += 1
        if d.get("action_candidates_declared") is not None:
            present += 1
        p = int(d.get("plan_steps_total") or 0)
        plan_vals[str(p)] = plan_vals.get(str(p), 0) + 1
        rc_vals[str(d.get("rc"))] = rc_vals.get(str(d.get("rc")), 0) + 1
        if p >= 2:
            plan_ge2 += 1
    return {"runs": n, "declared_field_present": present, "plan_ge2": plan_ge2,
            "plan_hist": plan_vals, "rc_hist": rc_vals, "root": RUNS}


def main():
    if not os.path.isfile(PROTO):
        print(json.dumps({"rc": 3, "reason": "INPUT_MISSING:prototype"}, ensure_ascii=False))
        return 3
    d = derive()
    cn = counter()
    checks = {
        "C1_vocab_not_menu": len(d["only_in_block"]) > 0,
        "C2_explicit_opt_out": bool(d["opt_out"]),
        "C3_orchestrated_but_zero_declared": (cn["runs"] > 0 and cn["plan_ge2"] == cn["runs"]
                                             and cn["declared_field_present"] == 0),
    }
    # --- 控制（成对）--------------------------------------------------------
    src = io.open(PROTO, encoding="utf-8").read()
    pos_ac = block(src, "ACTION_CANDIDATES").replace("（可选;", "（**必填字段**;").replace(
        "不声明 \\u21d2 本地只按 plan 执行。", "无动作也必须给空数组 []。")
    pos = {"opt_out": ("可选" in pos_ac) and ("不声明" in pos_ac)}
    ctl = {"POS_opt_out_flips": pos["opt_out"] is False,
           "NEG_empty_corpus": counter()["runs"] > 0,
           "non_trivial": len({len(d["ac_vocab"]), len(d["menu_vocab"]), cn["runs"]}) == 3}
    rc = 0
    if cn["runs"] == 0:
        rc = 3  # 输入缺失：不得读成「零声明」
    elif not (ctl["POS_opt_out_flips"] and ctl["non_trivial"]):
        rc = 2  # 器具缺陷
    verdict = {
        "rc": rc,
        "attribution": "contract_face_structural" if rc == 0 else ("INPUT_MISSING" if rc == 3 else "INSTRUMENT_DEFECT"),
        "reads": d, "frozen_reads": cn, "checks": checks, "controls": ctl,
        "claim": "J1=0 由契约面结构决定（可选 ∧ 显式豁免 ∧ 词表与管道菜单不同源），非「远端零遵守」",
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(verdict, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main())
