#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R497 判据器总闸: 臂表从 run_arm_real_r497.sh **机派生** (单一源), 逐臂跑全部面判据, 再跑轮级扫描。

用法: python3 judge_all_r497.py [--dir eval/rover/r497] [--skip-arm-face]
输出: 各判据器自己的 JSON + 控制台汇总表; 退出码 = 红项数>0 ? 1 : 0
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def arms_from_runner(runner):
    """从 runner 的 case 分支机派生臂表 (禁手抄)。"""
    txt = open(runner, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"^\s{2}([A-Za-z0-9]+)\)\s+MP=.*?CH=(\w+);\s*MOUNT=(\w+);\s*AB=(\w+)\s*;;", txt, re.M):
        out[m.group(1)] = {"channel": m.group(2), "mount": m.group(3), "ab": m.group(4)}
    for m in re.finditer(r"^\s{2}([A-Za-z0-9]+)\)\s+MP=.*?RS=(\w+);", txt, re.M):
        if m.group(1) in out:
            out[m.group(1)]["repeat_skip"] = m.group(2)
    return out


def run(cmd, tag):
    p = subprocess.run(cmd, capture_output=True, text=True)
    tail = [l for l in (p.stdout or "").strip().splitlines() if l.strip()][:14]
    print("  [%s] rc=%d" % (tag, p.returncode))
    for l in tail:
        print("      " + l)
    if p.returncode not in (0,) and p.stderr:
        print("      stderr: " + p.stderr.strip().splitlines()[-1][:200])
    return p.returncode, p.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "eval/rover/r497"))
    a = ap.parse_args()
    D = a.dir
    runner = os.path.join(D, "run_arm_real_r497.sh")
    arms = arms_from_runner(runner)
    if not arms:
        print("[致命] 臂表派生失败 (runner case 分支未匹配)")
        return 3
    print("[臂表] " + json.dumps(arms, ensure_ascii=False))
    grid = os.path.join(D, "grid/task-p17-code.json")
    reds, ran = [], []
    for arm, cfg in arms.items():
        calls = os.path.join(D, "calls-%s.jsonl" % arm)
        if not os.path.exists(calls):
            print("[skip] %s 无 calls (未跑/失败)" % arm)
            continue
        print("[arm %s] channel=%s mount=%s ab=%s" % (arm, cfg["channel"], cfg["mount"], cfg["ab"]))
        base = [
            ["python3", os.path.join(D, "face_ext_r497.py"), "--arm", arm, "--dir", D,
             "--mount", cfg["mount"], "--ab", cfg["ab"], "--canary", "R497-OOB-CANARY-9f3a1c7e"],
            ["python3", os.path.join(D, "judge_code_r497.py"), "--turns", os.path.join(D, "turns-%s.jsonl" % arm),
             "--calls", calls, "--tel", os.path.join(D, "tel-%s/host.jsonl" % arm),
             "--ledger", os.path.join(D, "ledger-%s.jsonl" % arm), "--grid", grid, "--arm", arm,
             "--mount", cfg["mount"], "--out", os.path.join(D, "judge-code-%s.json" % arm)],
            ["python3", os.path.join(D, "judge_adv_r497.py"), "--turns", os.path.join(D, "turns-%s.jsonl" % arm),
             "--json", os.path.join(D, "adv-%s.json" % arm)],
            ["python3", os.path.join(D, "judge_adv_r497.py"), "--turns", os.path.join(D, "turns-%s.jsonl" % arm),
             "--grid", grid, "--json", os.path.join(D, "adv-code-%s.json" % arm)],
            ["python3", os.path.join(D, "leak_check_r497.py"), "--dir", D, "--arm", arm, "--tag", "r497",
             "--mount", cfg["mount"], "--out", os.path.join(D, "leak-check-%s.json" % arm)],
        ]
        for cmd in base:
            tag = os.path.basename(cmd[1]).replace("_r497.py", "") + ":" + arm
            rc, _ = run(cmd, tag)
            ran.append((tag, rc))
            if rc != 0:
                reds.append(tag)
    print("[轮级] 全通道真值收口扫描")
    rc, _ = run(["python3", os.path.join(D, "truth_reclose_scan_r497.py"), "--dir", D,
                 "--arms", ",".join(arms.keys())], "truth_reclose")
    ran.append(("truth_reclose", rc))
    if rc != 0:
        reds.append("truth_reclose")
    print("[轮级] 器具↔产品逐位比对")
    rc, _ = run(["python3", os.path.join(D, "gate_port_parity_r497.py"),
                 "--out", os.path.join(D, "gate-parity-r497.json")], "gate_parity")
    ran.append(("gate_parity", rc))
    if rc != 0:
        reds.append("gate_parity")
    print("[轮级] 不可复算面")
    rc, _ = run(["python3", os.path.join(D, "nonrecompute_check_r497.py"), "--dir", D,
                 "--arms", ",".join(arms.keys()),
                 "--out", os.path.join(D, "nonrecompute-r497.json")], "nonrecompute")
    ran.append(("nonrecompute", rc))
    if rc != 0:
        reds.append("nonrecompute")
    print("[轮级] KPI/阶梯")
    rc, _ = run(["python3", os.path.join(D, "analyze_r497.py"), "--dir", D], "analyze")
    ran.append(("analyze", rc))
    if rc != 0:
        reds.append("analyze")
    print("\n[汇总] 跑了 %d 项; 红 %d 项: %s" % (len(ran), len(reds), reds))
    return 1 if reds else 0


if __name__ == "__main__":
    sys.exit(main())
