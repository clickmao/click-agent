#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q46 成对负控: 用**探针自身**的判定函数跑 pre/post 两形态, 证明围栏对本行真有判别力。

臂:
  A 前态行 (含「尚未回填」+「缺口」)          ⇒ 期望 hits == 1   (假开放项复现)
  B 后态行 (本轮改写文本)                     ⇒ 期望 hits == 0
  C 真开放项行 (「**下轮候选**: 未开始」)      ⇒ 期望 hits >= 1   (防「凡改即绿」的空心闸)
夹具为合成文档 (与真盘无关), 只有本脚本构造的块内字段参与判定。
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PROBE = os.path.join(ROOT, "scripts", "capability_cycle_status.py")

spec = importlib.util.spec_from_file_location("ccs_q46", PROBE)
assert spec is not None and spec.loader is not None
ccs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccs)

def _field_line(path: str, key: str) -> str:
    """回归样本**取自产物原文** (禁手打: 手打串会跟着常量一起被写入通道改写)。"""
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        for ln in fh.read().splitlines():
            if key in ln:
                return ln[2:] if ln.startswith("> ") else ln
    raise SystemExit(f"__MISSING__ key={key} in {path}")


DOC = os.path.join(ROOT, "docs", "reports", "dynamic-telemetry-eval-rollback-strategy.md")
NC = os.path.join(ROOT, "eval", "capability", "exp1-q46", "nc_prestate_doc.md")
STALE = _field_line(NC, "另一本台账")                     # 前态锚 (不可变提交 32125b7 的 blob)
NEW = _field_line(DOC, "EXP1-Q45 已闭合")                 # 现盘真机原文
REAL_OPEN = "- **下轮候选**: 未开始"


def probe_line(line: str) -> dict:
    doc = "## 7. 迭代状态快照\n\n> ### 最新状态\n>\n> " + line + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(doc)
        p = fh.name
    try:
        hits, diag = ccs.master_opens(p)
    finally:
        os.unlink(p)
    return {"hits": hits, "diag": diag}


def main() -> int:
    rc = 0
    a = probe_line(STALE)
    b = probe_line(NEW)
    c = probe_line(REAL_OPEN)
    print(f"CHK armA_stale hits={len(a['hits'])} (expect 1)  close_fenced={a['diag']['close_fenced']} "
          f"quoted_fenced={a['diag']['quoted_fenced']} neg_fenced={a['diag']['neg_fenced']}")
    print(f"CHK armB_new   hits={len(b['hits'])} (expect 0)  close_fenced={b['diag']['close_fenced']} "
          f"quoted_fenced={b['diag']['quoted_fenced']} neg_fenced={b['diag']['neg_fenced']}")
    print(f"CHK armC_realopen hits={len(c['hits'])} (expect >=1)")
    if len(a["hits"]) != 1:
        print("CHK armA=FAIL"); rc = 2
    if len(b["hits"]) != 0:
        print("CHK armB=FAIL"); rc = 2
    if len(c["hits"]) < 1:
        print("CHK armC=FAIL (判别力缺失: 凡改即绿)"); rc = 2
    if a["diag"]["close_fenced"] + a["diag"]["quoted_fenced"] + a["diag"]["neg_fenced"] != 0:
        print("CHK armA_fencing=UNEXPECTED (前态行本应无围栏命中)")
        rc = 2
    print(f"PAIR_EXIT={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
