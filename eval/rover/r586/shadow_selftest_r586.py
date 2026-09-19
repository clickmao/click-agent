"""R586 判据器影子自检 (零被测执行; 只喂合成/历史读数给 judge()).

判据器上线前先证明它「有牙」: 可判红、可判绿、器具缺陷可判 rc=2、缺侧 fail-closed rc=3。
不通过 ⇒ 判据器不可用, 不得据其出读数 (与 skill `kpi-eval-harness-design` 的影子自检同形)。

用例 (期望 rc):
  POS_ok        : 合成全过 (产品=真值=58)                ⇒ 0   (证明**可判绿**, 非恒红)
  HIST_r585     : **R585 原始读数** 逐条喂入本判据器        ⇒ 1   (跨轮数据上复现 R585 自己的判决 D=[-8,-3])
  NEG_floor     : D=[0,0,-16] 中位 0 但触底              ⇒ 1   (证明 floor 条件有牙: 中位过关也判红)
  NEG_validwin  : 2/3 窗真值自身失败 ⇒ 有效窗 1 < 2       ⇒ 1   (证明「证不出」= 判红, 非放行)
  NEG_steps     : 产品步数列全 None                       ⇒ 2   (读数面缺档 = 器具缺陷, 非被测读数)
  NEG_baddumps  : 任一跑次 bad_dumps 非空                 ⇒ 2   (器具缺陷优先于被测判据)
"""
from __future__ import annotations
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kpi_r586 as K  # noqa: E402

PREREG = json.load(io.open(os.path.join(HERE, "prereg-r586.json"), encoding="utf-8"))
THIS = json.load(io.open(os.path.join(HERE, "kpi-table-r586.json"), encoding="utf-8"))["readings"]
R585 = json.load(io.open(os.path.join(HERE, "..", "r585", "kpi-table-r585.json"), encoding="utf-8"))["readings"]

WINS = ["w157", "w158", "w159"]


def rec(arm, win, rep, side, pass_n, steps=None, plan=None, bad=None, total=58, all_pass=None):
    return {"arm": arm, "win": win, "rep": rep, "sub": "shadow", "side": side,
            "cases_pass": pass_n, "cases_total": total, "failed_cases": [],
            "all_pass": (pass_n == total) if all_pass is None else all_pass,
            "calls": 1, "new_prompt": 10, "prompt": 10, "completion": 10,
            "v_all": 0.9, "v_incr": 0.9, "bad_dumps": (bad or []), "rc": 0, "stage": None,
            "repair_rounds": 0, "exec_repairs": 0, "public_probe_failed": None,
            "steps_executed": steps, "plan_steps_total": plan}


def synth(product_by_win, truth_by_win, steps=7, bad=None):
    out = []
    for w in WINS:
        out.append(rec("C1", w, 1, "codex", truth_by_win[w], steps=None, plan=None))
        for rep in range(1, 4):
            out.append(rec("R586D", w, rep, "agent", product_by_win[w], steps=steps, plan=(10 if steps else None), bad=bad))
    return out


CASES = {
    "POS_ok": (synth({"w157": 58, "w158": 58, "w159": 58}, {"w157": 58, "w158": 58, "w159": 58}), 0),
    # 异轮臂名原样喂入 ⇒ 缺侧 fail-closed (禁静默读空判绿)
    "HIST_r585_foreign_arm": (R585, 3),
    # 臂名投影 (仅改名, 数字/逐窗一行不动) ⇒ 须复现 R585 自己的判决 D=[-8,-3] / 中位 -5.5 / rc=1
    "HIST_r585_projected": ([dict(r, arm="R586D" if r["arm"] == "R585D" else r["arm"]) for r in R585], 1),
    "NEG_floor": (synth({"w157": 58, "w158": 58, "w159": 42}, {"w157": 58, "w158": 58, "w159": 58}), 1),
    "NEG_validwin": (synth({"w157": 58, "w158": 58, "w159": 58},
                           {"w157": 50, "w158": 50, "w159": 58}), 1),
    "NEG_steps": (synth({"w157": 58, "w158": 58, "w159": 58},
                        {"w157": 58, "w158": 58, "w159": 58}, steps=None), 2),
    "NEG_baddumps": (synth({"w157": 58, "w158": 58, "w159": 58},
                           {"w157": 58, "w158": 58, "w159": 58}, bad=["shadow"]), 2),
}

res, ok = {}, True
for name, (recs, want) in CASES.items():
    v = K.judge(recs, PREREG)
    rc = v["verdict"]["rc"]
    got = {"rc": rc, "want": want, "C1_pass": v["C1_quality_paired"]["pass"],
           "D_list": v["C1_quality_paired"]["D_list"],
           "D_median": v["C1_quality_paired"]["D_median"],
           "valid_windows": v["C1_quality_paired"]["valid_windows"],
           "C0_pass": v["C0_truth_reliability"]["pass"],
           "C6_pass": v["C6_steps_face"]["pass"],
           "C5_state": v["C5_gap_reproduction"]["state"],
           "blocked": v["verdict"]["blocked"], "agree": rc == want}
    if name == "HIST_r585_projected":  # 跨轮复现须逐值相同, 不只看 rc
        got["reproduces_r585"] = (got["D_list"] == [-8, -3] and got["D_median"] == -5.5)
        got["agree"] = got["agree"] and got["reproduces_r585"]
    ok = ok and got["agree"]
    res[name] = got

out = {"round": "R586", "instrument": "shadow_selftest_r586.py",
       "mode": "零被测执行 (合成/历史读数直喂 judge())",
       "cases": res, "all_agree": ok,
       "note": "HIST_r585 = R585 原始读数 (跨轮数据) ⇒ 判据器须复现 R585 自己的 D=[-8,-3]/rc=1, "
               "以证判定按判据面计算而非硬编码本轮数字。"}
path = os.path.join(HERE, "shadow-selftest-r586.json")
json.dump(out, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"all_agree": ok, "out": path,
                  "cases": {k: {"rc": v["rc"], "want": v["want"],
                                "C1_pass": v["C1_pass"], "D": v["D_list"]} for k, v in res.items()}},
                 ensure_ascii=False))
sys.exit(0 if ok else 1)
