#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R632 · 披露式负控（三步，承 R629 形态）：证明「判据族对齐」这条判据**有牙**，且修法不放宽断言。

STEP1 修前窗口（现盘旧裁判件 `eval/rover/r631/judge_r631.py`）:
      其判据键族 vs `prereg-r631.json` 的 `criteria` 键族 ⇒ 必判**不同源**；
      另检「机读主判据键」「显式判决来源」两字段缺席。
STEP2 修后窗口（`eval/rover/r632/verdict-r632.json`）:
      D1 全绿（键集合逐键相等 ∧ 主判据键可机读 ∧ 全部键带声明状态）。
STEP3 牙证明（单变量变体，只在**副本/内存**上动）:
      ① 逐键删除 prereg 键（每次一个）⇒ 对齐判据必须转红（否则是恒真门）；
      ② 仅多一个键 ⇒ 转红（子集/超集都不得放行）；
      ③ 主判据键问不出（`primary` 标记缺失/多重）⇒ 转红（fail-closed）。

用法: python3 eval/rover/r632/nc_r632.py [--json <out>]
"""
import argparse
import copy
import io
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PD = os.path.join(REPO, "eval/rover/r632")
R631 = os.path.join(REPO, "eval/rover/r631")


def family_check(judge_keys, prereg_criteria):
    """D1 的纯函数核（与 judge_align_r632.py 同一谓词，供变体注入复算）。"""
    src = sorted(prereg_criteria.keys())
    prim = sorted([k for k, v in prereg_criteria.items() if v.get("primary")])
    return {"keys_equal": sorted(judge_keys) == src,
            "primary_key_readable": len(prim) == 1,
            "judge_keys_missing": sorted(set(src) - set(judge_keys)),
            "judge_keys_extra": sorted(set(judge_keys) - set(src))}


def old_judge_keys():
    src = io.open(os.path.join(R631, "judge_r631.py"), encoding="utf-8").read()
    pat = re.compile(r'"(J\d[a-z]?_[a-z0-9_]+|J\d_[a-z0-9_]+|W_[a-z0-9_]+|LD_[a-z0-9_]+|v3|C1_task_face_v3)"')
    keys = set(pat.findall(src))
    return sorted(k for k in keys if not re.match(r"^(J\d+$|v3$)", k))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(PD, "evidence", "nc-r632.json"))
    a = ap.parse_args()
    pre_src = json.load(io.open(os.path.join(R631, "prereg-r631.json"), encoding="utf-8"))
    pre_self = json.load(io.open(os.path.join(PD, "prereg-r632.json"), encoding="utf-8"))
    rows = []

    # ---- STEP1 修前 ----
    ok = old_judge_keys()
    f1 = family_check(ok, pre_src["criteria"])
    v631 = json.load(io.open(os.path.join(R631, "verdict-r631.json"), encoding="utf-8"))
    s1 = {"keys_equal": f1["keys_equal"], "judge_keys_missing": f1["judge_keys_missing"],
          "judge_keys_extra": f1["judge_keys_extra"],
          "primary_criterion_key_present": ("primary_criterion_key" in v631),
          "verdict_source_present": ("verdict_source" in v631),
          "declared_primary_in_prereg": f1["primary_key_readable"]}
    step1_red = (not s1["keys_equal"]) and (not s1["primary_criterion_key_present"]) \
        and (not s1["verdict_source_present"])
    rows.append({"step": "STEP1_pre_fix", "expect": "RED(判据族不同源+两机读字段缺席)", "red": bool(step1_red),
                 "detail": s1})

    # ---- STEP2 修后 ----
    v632 = json.load(io.open(os.path.join(PD, "verdict-r632.json"), encoding="utf-8"))
    d1 = v632["D1_judge_family_aligned"]
    s2 = {"keys_equal": d1["keys_equal"], "primary_key_readable": d1["primary_key_readable"],
          "all_keys_present_with_declared_state": d1["all_keys_present_with_declared_state"],
          "primary_criterion_key": v632["criterion_source"]["primary_criterion_key"],
          "verdict_source_present": ("verdict_source" in v632),
          "verdict_source": v632["verdict_source"]["key"]}
    step2_green = bool(d1["pass"] and s2["verdict_source_present"])
    rows.append({"step": "STEP2_post_fix", "expect": "GREEN(D1 pass ∧ 来源显式)", "green": bool(step2_green),
                 "detail": s2})

    # ---- STEP3 牙证明 ----
    jk = v632["criterion_source"]["criteria_keys_judge"]
    variants = []
    for k in sorted(pre_src["criteria"].keys()):
        m = copy.deepcopy(pre_src["criteria"])
        m.pop(k)
        variants.append({"variant": "drop:%s" % k, "expect": "keys_equal=False",
                         "got": family_check(jk, m)["keys_equal"]})
    m = copy.deepcopy(pre_src["criteria"])
    m["J9_invented_extra"] = {"kind": "instrument", "need": "x"}
    variants.append({"variant": "add:J9_invented_extra", "expect": "keys_equal=False",
                     "got": family_check(jk, m)["keys_equal"]})
    m = copy.deepcopy(pre_src["criteria"])
    m["J4a_capability_replication"]["primary"] = True
    variants.append({"variant": "dup:primary×2", "expect": "primary_key_readable=False",
                     "got": family_check(jk, m)["primary_key_readable"]})
    teeth = all((v["got"] is False) for v in variants)
    step3 = {"variants": variants, "teeth": bool(teeth),
             "note": "逐键删除/多键/主判据键多重 ⇒ 全部必须转红（否则 D1 是恒真门）"}
    rows.append({"step": "STEP3_teeth", "expect": "全部变体转红", "teeth": bool(teeth)})

    rc = 0 if (step1_red and step2_green and teeth) else 2
    out = {"round": "R632", "kind": "披露式负控（三步）—— 判据族对齐判据的牙证明",
           "rc": rc, "step1_pre_fix_red": bool(step1_red), "step2_post_fix_green": bool(step2_green),
           "step3_teeth": bool(teeth), "rows": rows, "variants": step3["variants"],
           "note": "修前读数**原样保留、不翻案**：旧裁判件判决仍不予采用（R631 自捕 D2）",
           "old_judge_keys": ok, "prereg_keys": sorted(pre_src["criteria"].keys())}
    json.dump(out, io.open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": rc, "step1_red": bool(step1_red), "step2_green": bool(step2_green),
                      "teeth": bool(teeth), "missing": s1["judge_keys_missing"],
                      "extra": s1["judge_keys_extra"], "variants_false": sum(1 for v in variants if v["got"] is False),
                      "variants_n": len(variants)}, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
