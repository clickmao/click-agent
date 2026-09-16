#!/usr/bin/env python3
"""R505 证据冻结/复核: 跨时间第二次取数（H9）+ 二次归因 + 多批汇总 + 一页交接。

用法:
  python3 eval/rover/r505/make_evidence_r505.py            # 冻结: 复核 + 归因 + 汇总 + README + 指纹
  python3 eval/rover/r505/make_evidence_r505.py --verify   # 只复核（rc: 0 全绿 / 2 有失配）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PY = sys.executable
EV = os.path.join(HERE, "evidence")
BATCHES = ["a", "b", "c"]


def load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def replay_all():
    """跨时间第二次取数: 冻结清单 → 快照目录（判分后、另一进程）"""
    res = {}
    for b in BATCHES:
        for side in ("codex", "agent"):
            d = os.path.join(EV, b, "adapter-%s" % side)
            usage = os.path.join(d, "usage-%s.txt" % side)
            if not os.path.exists(usage):
                res["%s/%s" % (b, side)] = {"rc": 3, "why": "缺冻结清单"}
                continue
            out = os.path.join(EV, b, "replay-%s-%s-late.json" % (side, b))
            rc, _ = run([PY, os.path.join(HERE, "check_usage_replay.py"),
                         "--usage", usage, "--dir", d, "--out", out])
            res["%s/%s" % (b, side)] = {"rc": rc, "out": os.path.relpath(out, REPO),
                                        "replayable": load(out).get("replayable") if os.path.exists(out) else None}
    return res


def attributed():
    res = {}
    for b in BATCHES:
        side_dirs = {"agent": os.path.join(EV, b, "adapter-agent")}
        for side, d in side_dirs.items():
            if not os.path.isdir(d):
                res["%s/%s" % (b, side)] = {"rc": 3}
                continue
            out = os.path.join(EV, b, "attr-%s-%s.json" % (side, b))
            rc, _ = run([PY, os.path.join(HERE, "attr_calls_r505.py"), "--dir", d,
                         "--manifest", os.path.join(d, "manifest-agent.json"),
                         "--tag", "agent-r505%s" % b, "--out", out])
            res["%s/%s" % (b, side)] = {"rc": rc, "out": os.path.relpath(out, REPO)}
    return res


def readme(agg, rep, attr):
    lines = ["# R505 证据一页（主线对照: 外部真值 codex-cli × 本侧 AOT agenthost, 同题集 11 题）", ""]
    lines.append("| 批 | rc | codex 整题全对 | codex 调用 | codex tokens | 本侧整题全对 | 本侧调用 | 本侧 tokens |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in agg.get("per_batch") or []:
        if r.get("status") == "missing":
            lines.append("| %s | 缺产物 | | | | | | |" % r["batch"])
            continue
        lines.append("| %s | %d | %d/%d | %d | %d | %d/%d | %d | %d |" % (
            r["batch"], r["rc"], r["codex"]["whole_ok"], r["codex"]["n"], r["codex"]["calls"],
            r["codex"]["tok"], r["agent"]["whole_ok"], r["agent"]["n"], r["agent"]["calls"], r["agent"]["tok"]))
    h7 = agg.get("H7") or {}
    h8 = agg.get("H8") or {}
    lines += ["", "## 判据（预注册口径）",
              "- H7 质量面: codex %s/%s | 本侧 %s/%s | mode 逐题一致 %s/%s ⇒ %s" % (
                  h7.get("codex_ok_total"), h7.get("obs_total"), h7.get("agent_ok_total"),
                  h7.get("obs_total"), h7.get("mode_agree"), h7.get("obs_total"),
                  "PASS" if h7.get("pass") else "NOT"),
              "- H8 调用构成: 本侧逐批调用数 %s | 均值 %s | 目标 ≤%s ⇒ %s | 归因覆盖 %s" % (
                  [r.get("agent", {}).get("calls") for r in agg.get("per_batch") or [] if r.get("agent")],
                  h8.get("agent_calls_mean"), h8.get("calls_target"),
                  "达标" if h8.get("target_met") else "未达标", "全归位" if h8.get("coverage_pass") else "有未归因"),
              "- H9 跨时间复核: %s" % ("PASS" if (agg.get("H9_cross_time") or {}).get("pass") else "NOT")]
    lines += ["", "## 逐题调用构成（本侧, 三批合计）"]
    for tid, n in sorted((h8.get("calls_by_task_sum") or {}).items()):
        lines.append("- %s: %d 次" % (tid, n))
    lines += ["", "## 跨时间复核明细"]
    for k in sorted(rep):
        lines.append("- %s: rc=%s replayable=%s" % (k, rep[k].get("rc"), rep[k].get("replayable")))
    lines += ["", "## 归因器二次取数"]
    for k in sorted(attr):
        lines.append("- %s: rc=%s %s" % (k, attr[k].get("rc"), attr[k].get("out")))
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    rep = replay_all()
    bad = [k for k, v in rep.items() if v.get("rc") != 0]
    if a.verify:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        print("复核结论: %s" % ("全绿" if not bad else "失配 %s" % bad))
        return 0 if not bad else 2
    attr = attributed()
    rc, out = run([PY, os.path.join(HERE, "agg_r505.py"), "--batches"] + BATCHES)
    print(out.strip().splitlines()[-1] if out.strip() else "")
    agg = load(os.path.join(EV, "agg-r505.json"))
    txt = readme(agg, rep, attr)
    with open(os.path.join(EV, "README-r505.md"), "w", encoding="utf-8") as fh:
        fh.write(txt)
    fingers = {}
    for root, _dirs, files in os.walk(EV):
        for f in sorted(files):
            p = os.path.join(root, f)
            if os.path.getsize(p) < 4_000_000:
                fingers[os.path.relpath(p, REPO)] = sha(p)
    with open(os.path.join(EV, "FINGERPRINTS-r505.json"), "w", encoding="utf-8") as fh:
        json.dump({"prereg": {"path": os.path.relpath(os.path.join(HERE, "prereg_r505.json"), REPO),
                              "sha256": sha(os.path.join(HERE, "prereg_r505.json"))},
                   "files": fingers, "agg_rc": rc}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(txt)
    print("指纹件数: %d -> %s" % (len(fingers), os.path.relpath(os.path.join(EV, "FINGERPRINTS-r505.json"), REPO)))
    return 0 if (not bad and rc == 0) else 2


if __name__ == "__main__":
    raise SystemExit(main())