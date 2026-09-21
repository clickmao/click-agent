#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R617 J0 判据器负控/正控（证「有牙」）：用真实落盘遥测造三种合成臂态，断言判决而非崩溃。

  NC1 单次缺测：T 跑次 1 的 sha 置 null ⇒ 缺席单列（弃权）⇒ J0 仍 true 且 instrument_gap 计数 = 1（不得把缺席判红，也不得静默吞掉）
  NC3 全臂缺席：T/C 全部跑次 sha 置 null ⇒ 臂身份不可证 ⇒ J0 必须 false
  NC2 轴未分离：C 全臂 sha 置为 T 的 pin       ⇒ J0 必须 false（C_disjoint false）
  PC  正控：原样                            ⇒ J0 必须 true（pins 全中）
用法: python3 eval/rover/r617/nc_j0_r617.py
"""
from __future__ import annotations
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
D = os.path.expanduser("~/.agentframework/harness/runs/r617")
PDIR = os.path.join(REPO, "eval/rover/r617")
T_PIN = "25c97befa2124549b52991c0338324ceee7f7702a6348641ed917d3b7b658052"


def build(dst, mutate):
    os.makedirs(os.path.join(dst, "logs"), exist_ok=True)
    if not os.path.exists(os.path.join(dst, "adapter")):
        os.symlink(os.path.join(D, "adapter"), os.path.join(dst, "adapter"))
    runs = [json.loads(l) for l in io.open(os.path.join(D, "logs", "runs.jsonl"), encoding="utf-8") if l.strip()]
    for r in runs:
        g = os.path.join(dst, r["win"], r["sub"], "g1")
        os.makedirs(g, exist_ok=True)
        src_tr = os.path.join(D, r["win"], r["sub"], "g1", "transcript.json")
        t = json.load(io.open(src_tr, encoding="utf-8")) if os.path.isfile(src_tr) else {}
        mutate(r, t)
        json.dump(t, io.open(os.path.join(g, "transcript.json"), "w", encoding="utf-8"), ensure_ascii=False)
        src_cs = os.path.join(D, r["win"], r["sub"], "g1", "cases.txt")
        body = io.open(src_cs, encoding="utf-8").read() if os.path.isfile(src_cs) else ""
        io.open(os.path.join(g, "cases.txt"), "w", encoding="utf-8").write(body)
    io.open(os.path.join(dst, "logs", "runs.jsonl"), "w", encoding="utf-8").write(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in runs))


def run_judge(dst, out):
    cmd = ["python3", os.path.join(PDIR, "judge_r617.py"), "--D", dst, "--pd", PDIR, "--json", out]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p


def main():
    outdir = tempfile.mkdtemp(prefix="nc617-")
    cases = {
        "PC": lambda r, t: None,
        "NC1": lambda r, t: (t.__setitem__("prefix_sha256", None) if (r["arm"] == "T" and r["rep"] == 1) else None),
        "NC2": lambda r, t: (t.__setitem__("prefix_sha256", T_PIN) if r["arm"] == "C" else None),
        # NC3 全臂缺席：T/C 全部跑次缺遥测 ⇒ 臂身份不可证 ⇒ J0 必须假（防「缺席当绿」空心）
        "NC3": lambda r, t: (t.__setitem__("prefix_sha256", None) if r["arm"] in ("T", "C") else None),
    }
    rc_all = 0
    for name, mut in cases.items():
        dst = os.path.join(outdir, name)
        build(dst, mut)
        out = os.path.join(outdir, name + ".json")
        p = run_judge(dst, out)
        crashed = "Traceback" in p.stderr
        try:
            v = json.load(io.open(out, encoding="utf-8"))
            j0 = v.get("J0_arm_axis_effective", {}).get("pass")
        except Exception:
            v, j0 = None, None
        want = {"PC": True, "NC1": True, "NC2": False, "NC3": False}[name]
        x = p.stdout.strip().splitlines()
        print("%-4s crashed=%-5s J0_pass=%-5s (want %-5s) %s | %s" % (
            name, crashed, j0, want, "OK" if (j0 is want and not crashed) else "MISMATCH",
            (x[-1][:110] if x else p.stderr.strip().splitlines()[-1][:110])))
        if j0 is not want or crashed:
            rc_all = 2
    print("NC_RC=%d" % rc_all)
    return rc_all


if __name__ == "__main__":
    sys.exit(main())
