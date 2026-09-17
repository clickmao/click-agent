#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R515 读数汇总: 用例真值取 grade_r511.py 落盘; 调用/tokens 真值取 adapter 落盘并按臂索引区间归属。

口径:
  * 用例: grade-<arm>.json 的 cases_passed / cases_total / ok / failed[]。
  * 调用与 tokens: side-agent-NNN.json (adapter 真值), 按 idx-before/idx-after 区间归属;
    区间内无 usage ⇒ usage=null (unreported), **禁冒充 0**。
  * 编排器侧: orch/report.json (state / budget_ceiling / overlap_ms / nodes[])。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "r511"))
import usage_from_dumps as U  # type: ignore  # 复用 R511 已入库的同一读取器 (同口径)


def load(path: str):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def idx(d: str, name: str):
    try:
        with open(os.path.join(d, name), encoding="utf-8") as fh:
            return int(fh.read().strip())
    except Exception:
        return None


def arm_row(d: str, tag: str) -> dict:
    g = load(os.path.join(d, "grade-%s.json" % tag)) or {}
    i0, i1 = idx(d, "%s/idx-before" % tag), idx(d, "%s/idx-after" % tag)
    usage = None
    if i0 is not None and i1 is not None and i1 > i0:
        u = U.collect(os.path.join(d, "adapter"), "agent", i0 + 1, i1)
        usage = {k: u.get(k) for k in ("calls", "prompt_tokens", "cached_tokens",
                                      "completion_tokens", "total_tokens", "unreported_usage")}
        usage["models"] = u.get("models")
    return {
        "arm": tag,
        "cases_passed": g.get("cases_passed"),
        "cases_total": g.get("cases_total"),
        "ok": g.get("ok"),
        "grade_rc": g.get("rc"),
        "failed": [f.get("name") for f in (g.get("failed") or [])],
        "dump_range": [i0, i1],
        "usage": usage,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    d = a.run_dir

    rows = [arm_row(d, "single"), arm_row(d, "orch")]
    orch = load(os.path.join(d, "orch/report.json"))
    out = {"run_dir": d, "arms": rows, "orchestrator": orch}

    print("== R515 读数 (同窗·同题面·同模型) ==")
    for r in rows:
        u = r["usage"] or {}
        print("臂 %-6s 用例 %s/%s ok=%s rc=%s 调用=%s tokens=%s" % (
            r["arm"], r["cases_passed"], r["cases_total"], r["ok"], r["grade_rc"],
            u.get("calls", "unreported") if r["usage"] else "unreported",
            u.get("total_tokens", "unreported") if r["usage"] else "unreported"))
        if r["failed"]:
            print("   失败用例(%d): %s" % (len(r["failed"]), ",".join(r["failed"])))
    if orch:
        print("编排器: state=%s 节点预算上限=%s 墙钟重叠=%sms" % (
            orch.get("state"), orch.get("budget_ceiling"), orch.get("overlap_ms")))
        for n in orch.get("nodes") or []:
            print("   %-4s L%-2s %-8s %-10s %6sms out=%sB files=%s %s" % (
                n.get("node_id"), n.get("level"), n.get("location"), n.get("state"),
                n.get("elapsed_ms"), n.get("output_chars"),
                ",".join(n.get("files") or []) or "-", n.get("error") or ""))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
