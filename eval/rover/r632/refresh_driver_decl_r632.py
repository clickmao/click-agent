#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R632 · 候选③ 的**修复件**：刷新 `eval/rover/r631/run_r631.sh` 的头部声明块，使其逐项等于实盘赋值。

纪律（承 EXP1-Q38 A / R632 prereg D3+D4）:
  * **只改注释（声明）文本**；`set -uo pipefail` 之后的实盘段 sha256 **必须逐字节不变**（机检，不符即拒写）；
  * 修前/修后头部原文**归档留痕**（`evidence/decl-refresh-r631.json`），**历史判决与读数不改写**；
  * 幂等：重跑不产生新差异（已对齐 ⇒ 二次运行为 no-op）。
用法: python3 eval/rover/r632/refresh_driver_decl_r632.py [--apply]
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PD = os.path.join(REPO, "eval/rover/r632")
TARGET = os.path.join(REPO, "eval/rover/r631/run_r631.sh")

sys.path.insert(0, PD)
import decl_driver_check_r632 as chk  # noqa: E402


def sha(b):
    return hashlib.sha256(b).hexdigest()


def refresh_text(text, lv):
    """逐项替换声明（幂等：目标串不存在时跳过），并在末尾追加 ⑨ 刷新登记行。"""
    ws = lv.get("win_set") or []
    new_title = ("# R631 驱动器（RF0004.2 · M3 **执行面轴 `AGENTFRAMEWORK_R1_ACTION_EXEC` 跨窗复现轮**: "
                 "2 窗 × reps3 × 2 臂 + codex 真值 ×1/窗）——")
    subs = [
        (r"# R631 驱动器（RF0004\.2 · M3 \*\*第五刀 = 等价面分辨率取证（reps 3→6）\+ 判据分级\*\*）——",
         new_title),
        (r"端口 49792→49793", "端口 49792→%s" % lv.get("port")),
        (r"窗号 WIN0 208→\*\*211\*\*（w211\.\.w213；与历史窗集 w184\.\.w210 \*\*不相交\*\*）",
         "窗号 WIN0 208→**%s**（w%s..w%s；与历史窗集 w184..w%s **不相交**）"
         % (lv.get("win0"), ws[0][1:], ws[-1][1:], "w%d" % (int(ws[0][1:]) - 1))),
        (r"sha 886db888d744a619…", "sha %s…" % lv.get("bin_sha16")),
        (r"PREV_SWING = \*\*125MB\*\*（口径 = R631 起手闸 `--min-avail-mb 2775` − 产品门槛 2650；",
         "PREV_SWING = **%sMB**（口径 = R631 起手闸 `--min-avail-mb %s` − 产品门槛 2650；"
         % (lv.get("prev_swing_mb"), lv.get("min_avail_mb"))),
    ]
    for pat, rep in subs:
        text = re.sub(pat, rep, text, count=1)
    reg = ("#   ⑨ **声明刷新（R632 器件面收口 · 候选③）**：本头部声明块逐项与实盘赋值对齐（器 "
           "`eval/rover/r632/decl_driver_check_r632.py`；修前 6/6 漂移，见 `eval/rover/r632/evidence/"
           "decl-before-r631.json`）。**只改注释**，`set -uo pipefail` 之后实盘段逐字节未动。\n")
    if "⑨ **声明刷新（R632" not in text:
        text = text.replace("# 用法: bash eval/rover/r631/run_r631.sh",
                            reg + "# 用法: bash eval/rover/r631/run_r631.sh", 1)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    before = io.open(TARGET, encoding="utf-8").read()
    hdr_b, body_b = chk.split_driver(before)
    lv, _ = chk.live_values("r631")
    after = refresh_text(before, lv)
    hdr_a, body_a = chk.split_driver(after)
    out = {"round": "R632", "target": "eval/rover/r631/run_r631.sh",
           "mode": "apply" if a.apply else "dry-run",
           "sha256_before": sha(before.encode("utf-8")), "sha256_after": sha(after.encode("utf-8")),
           "header_sha256_before": sha(hdr_b.encode("utf-8")), "header_sha256_after": sha(hdr_a.encode("utf-8")),
           "body_sha256_before": sha(body_b.encode("utf-8")), "body_sha256_after": sha(body_a.encode("utf-8")),
           "body_unchanged": sha(body_b.encode("utf-8")) == sha(body_a.encode("utf-8")),
           "header_before": hdr_b, "header_after": hdr_a,
           "note": "只改注释声明；实盘段（set -uo pipefail 之后）sha256 必须逐字节不变（D4 机检）"}
    if not out["body_unchanged"]:
        print("BODY_CHANGED 拒写 (fail-closed)")
        json.dump(out, io.open(os.path.join(PD, "evidence", "decl-refresh-r631.json"), "w",
                               encoding="utf-8"), ensure_ascii=False, indent=1)
        return 2
    if a.apply:
        io.open(TARGET, "w", encoding="utf-8").write(after)
        back = io.open(TARGET, encoding="utf-8").read()
        out["readback_sha256"] = sha(back.encode("utf-8"))
        out["readback_matches"] = out["readback_sha256"] == out["sha256_after"]
        out["idempotent_second_pass"] = (refresh_text(back, lv) == back)
    json.dump(out, io.open(os.path.join(PD, "evidence", "decl-refresh-r631.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("mode", "body_unchanged", "sha256_before", "sha256_after",
                                          "readback_matches", "idempotent_second_pass")
                      if k in out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
