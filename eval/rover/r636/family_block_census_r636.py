#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R636 · `B_family_block` **真机两侧有牙**取证 + 跨轮 base rate census（**只读**，零重测/零远端）。

为什么需要这一件（承 skill 纪律「判据上线前先跑影子自检」＋「有牙三件套」）：
  · `judge_r636.py --selftest` 只覆盖**合成**三态（FAMILY_BLOCK / CLEAN / PARTIAL_FAMILY）——合成件
    由我构造，只能证明「分类器不是恒真门」，**不能**证明它在**真机产物形态**上判得对。
  · 本条在**冻结跑次**上取两侧样例：一个真机 `FAMILY_BLOCK` 跑次（应判红）与一个真机 `CLEAN` 跑次
    （应判绿）——**只跑一侧 = 未证有牙**（会把「恒红」或「恒绿」读成「有判别力」）。
  · 口径**不重写第二份**：分类逻辑直接 import `judge_r636.family_block_core`（禁自证/禁第二实现）。

读数用途（全部**并列**，不作能力结论）：
  · `base_rate`：本侧跑次里「整族归零」出现的频率（R635 已知 1/9 命中）——把 R635 的**单点**现象
    放到跨轮分布里看，回答候选②「是否该给这类跑次独立分类」。
  · `blocking_family`：归零的是哪个族（承 R621/R622 登记的 `wythoff` 承重缺口）。

退出码三态（承 skill「断言失败 / 测量失败 / 环境失败」不同码）：
  0 = 两侧样例均按预期 ∧ census 完成；2 = 判据/有牙失败；3 = 输入缺失（冻结跑次不在盘上）。
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
JUDGE = os.path.join(REPO, "eval/rover/r636/judge_r636.py")
HARNESS = os.path.expanduser("~/.agentframework/harness/runs")
ROUNDS = ("r631", "r633", "r634", "r635", "r636")
# 两侧真机样例（钉死在**冻结**命名空间上；缺任一 ⇒ rc=3，不用「近似样例」替代）
TEETH_POS = ("r635", "w232", "agentP-r2")   # 真机整族归零跑次 ⇒ 必判 FAMILY_BLOCK
TEETH_NEG = ("r635", "w231", "agentP-r1")   # 真机全过跑次 ⇒ 必判 CLEAN


def load_judge():
    spec = importlib.util.spec_from_file_location("judge_r636", JUDGE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def iter_agent_case_files():
    """产出 (round, win, sub, cases_path)：只取本侧（agent*）跑次的判分件。"""
    for R in ROUNDS:
        root = os.path.join(HARNESS, R)
        if not os.path.isdir(root):
            continue
        for win in sorted(os.listdir(root)):
            wdir = os.path.join(root, win)
            if not os.path.isdir(wdir) or not win.startswith("w"):
                continue
            for sub in sorted(os.listdir(wdir)):
                if not sub.startswith(("agent", "DC", "DT")):
                    continue
                p = os.path.join(wdir, sub, "g1", "cases.txt")
                if os.path.isfile(p):
                    yield R, win, sub, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r636/family-block-census-r636.json"))
    a = ap.parse_args()
    j = load_judge()

    def read_cli_rc(cases_path):
        """cli_rc 与判分件同目录（g1/cli_rc.txt）；缺失记 None。"""
        p = os.path.join(os.path.dirname(cases_path), "cli_rc.txt")
        if not os.path.isfile(p):
            return None
        try:
            return int(io.open(p, encoding="utf-8", errors="replace").read().strip())
        except Exception:  # noqa: BLE001
            return None

    rows, missing = [], []
    for R, win, sub, path in iter_agent_case_files():
        cs = j.read_cases(path)
        cli_rc = read_cli_rc(path)
        # **VOID 形态判定与判据器同源**（judge_r636.main 的同两条）：同质超时 / 臂自身超时。
        # 首跑（v1prevoid）缺这一步 ⇒ 把 r633:w227/agentP-r2（cli_rc=124 整轮挂死）读成 FAMILY_BLOCK
        # ⇒ 「挂死」与「整族归零」被混成一类。**修输入集，不改分类器**（判据零放宽），首跑读数留档。
        void = bool(cs["total"] and cs["timeouts"] == (cs["total"] - cs["pass"]) and cs["timeouts"] > 0) \
            or bool(cli_rc == 124 and cs["pass"] < cs["total"])
        rows.append({"harness_round": R, "win": win, "sub": sub,
                     "cases_pass": cs["pass"], "cases_total": cs["total"], "cli_rc": cli_rc,
                     "timeouts": cs["timeouts"], "void": void,
                     "families": {f: "%d/%d" % (v["pass"], v["total"]) for f, v in sorted(cs["families"].items())},
                     "_fams": cs["families"]})
    for t in (TEETH_POS, TEETH_NEG):
        if not any((r["harness_round"], r["win"], r["sub"]) == t for r in rows):
            missing.append("%s/%s/%s" % t)

    # 口径同源：把 census 行喂给**判据器本体**的分类核（不自写第二份）；VOID 跑次先剔除并单列
    # （与 judge_r636.main 的 `recs_q = [r for r in recs if not r["void"]]` 同构）。
    rows_q = [r for r in rows if not r["void"]]
    void_runs = ["%s:%s/%s" % (r["harness_round"], r["win"], r["sub"]) for r in rows if r["void"]]
    recs = [{"arm": "P", "win": "%s:%s" % (r["harness_round"], r["win"]), "sub": r["sub"], "side": "agent",
             "cases_pass": r["cases_pass"], "cases_total": r["cases_total"],
             "fail_families": r["_fams"]} for r in rows_q]
    core = j.family_block_core(recs)
    cls = {"%s:%s" % (r["harness_round"], r["win"]) + "/" + r["sub"]: c["class"]
           for r, c in zip(rows_q, core["by_run"])}

    by_round = {}
    for r, c in zip(rows_q, core["by_run"]):
        b = by_round.setdefault(r["harness_round"], {"n_runs": 0, "n_family_block": 0,
                                                     "n_partial_family": 0, "n_clean": 0,
                                                     "blocking_families": {}, "runs": []})
        b["n_runs"] += 1
        b["n_" + c["class"].lower()] += 1
        for f in c["family_block_families"]:
            b["blocking_families"][f] = b["blocking_families"].get(f, 0) + 1
        b["runs"].append({"win": r["win"], "sub": r["sub"], "cases": "%d/%d" % (r["cases_pass"], r["cases_total"]),
                          "class": c["class"], "blocked": c["family_block_families"]})

    n, nb = core["n_runs"], core["n_family_block"]
    teeth = {
        "POS_expected": "FAMILY_BLOCK", "POS_sample": "%s/%s/%s" % TEETH_POS,
        "POS_got": cls.get("%s:%s/%s" % TEETH_POS),
        "NEG_expected": "CLEAN", "NEG_sample": "%s/%s/%s" % TEETH_NEG,
        "NEG_got": cls.get("%s:%s/%s" % TEETH_NEG),
    }
    teeth["pass"] = bool(teeth["POS_got"] == "FAMILY_BLOCK" and teeth["NEG_got"] == "CLEAN"
                         and not missing)
    out = {
        "round": "R636", "instrument": "family_block_census_r636.py",
        "role": ("`B_family_block` 的**真机两侧有牙**取证 + 跨轮 base rate census（只读冻结跑次；零重测/零远端）；"
                 "分类口径直接 import judge_r636.family_block_core（**不重写第二份**）"),
        "teeth": teeth,
        "missing_teeth_samples": missing,
        "census": {"rounds_scanned": list(ROUNDS), "n_agent_runs": n,
                   "void_runs_excluded": void_runs, "n_void_excluded": len(void_runs),
                   "n_family_block": nb, "n_partial_family": core["n_partial_family"], "n_clean": core["n_clean"],
                   "base_rate_family_block": (round(nb / n, 4) if n else None),
                   "family_blocked_runs": core["family_blocked_runs"], "by_round": by_round},
        "honest_bounds": [
            "census 只覆盖**在盘**的冻结跑次；已清理的轮次缺席 ⇒ 分母非全史（缺席单列 missing_teeth_samples 只针对两侧样例）",
            "VOID 跑次（同质超时 / cli_rc=124）**先剔除并单列**（与判据器同源）⇒ 「挂死」不被读成「整族归零」；"
            "首跑（`family-block-census-r636-v1prevoid.json`）缺此步、把 r633:w227/agentP-r2 误列 FAMILY_BLOCK，**留档不翻案**",
            "各轮的臂名不同（r631 = agentT/agentC；r633–r636 = agentP）⇒ 跨轮只**并列**，禁相减",
            "本件只判「是否整族归零」形态，**不提供机理归因**（机理归因须另开只读定因轮，承 R622 先例）",
            "`base_rate` 是**描述性**读数，不作阈值、不进任何 rc",
        ],
        "rc": 0 if teeth["pass"] else (3 if missing else 2),
        "rc_semantics": "0 两侧有牙且 census 完成 / 2 判据（有牙）失败 / 3 输入缺失（冻结样例不在盘）",
    }
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"rc": out["rc"], "teeth": teeth["pass"], "POS": teeth["POS_got"], "NEG": teeth["NEG_got"],
                      "n_agent_runs": n, "n_family_block": nb, "base_rate": out["census"]["base_rate_family_block"],
                      "void_excluded": void_runs, "blocked": core["family_blocked_runs"], "missing": missing}, ensure_ascii=False))
    return out["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
