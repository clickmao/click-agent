#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R564 · w115 单窗 −15 的族级**只读**定因 (候选④) —— 复用 R562 定因器具, 只换窗集。

零逻辑复制: 本文件是 **driver**, 全部定因逻辑 (分类器 / 独立 oracle / 逐例重放 / 摆动弹窗读数)
来自 `eval/rover/r562/wythoff_cause_r562.py` (import 后只替换三处**窗集常量**:
WINDOW_MAP / WINDOWS / ARMS)。R562 器具源码本文件**一字未改**, 其 sha256 登记在本轮读数件里
(证明差异只是窗集, 不是逻辑)。

窗集: R563 的 w113..w118 × 臂 {C1 = 外部真值 codex, R563B0 = 本侧产品默认档}。
快照 (只读, 判分在**副本**上做): eval/rover/r563/snapshots/<win>/<arm>/g1/

用法: python3 eval/rover/r564/wythoff_cause_r564.py [--out <path>] [--copies <dir>]
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
SRC = os.path.join(REPO, "eval/rover/r562/wythoff_cause_r562.py")
WINS = ["w113", "w114", "w115", "w116", "w117", "w118"]
ARM_LIST = ["C1", "R563B0"]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module():
    spec = importlib.util.spec_from_file_location("wythoff_cause_r562_reused", SRC)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wythoff_cause_r562_reused"] = mod
    spec.loader.exec_module(mod)          # 只 import, 不改源码
    mod.WINDOW_MAP = {w: ("r563", list(ARM_LIST)) for w in WINS}
    mod.WINDOWS = list(WINS)
    mod.ARMS = list(ARM_LIST)
    return mod


def main() -> int:
    out = os.path.join(REPO, "eval/rover/r564/wythoff-cause-r564.json")
    copies = "/tmp/r564/copies"
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    if "--copies" in sys.argv:
        copies = sys.argv[sys.argv.index("--copies") + 1]
    mod = load_module()
    os.makedirs(copies, exist_ok=True)
    saved_argv = sys.argv
    sys.argv = ["wythoff_cause_r564.py", "--out", out, "--copies", copies]
    try:
        rc = mod.main()
    finally:
        sys.argv = saved_argv
    if rc != 0:
        print(json.dumps({"rc": rc, "note": "reused instrument fail-closed (oracle/selftest)"}, ensure_ascii=False))
        return rc
    d = json.load(io.open(out, encoding="utf-8"))
    d["round"] = "R564"
    d["instrument"] = "wythoff_cause_r564.py (driver) -> wythoff_cause_r562.py (logic, unmodified)"
    d["reuse_binding"] = {
        "logic_source": "eval/rover/r562/wythoff_cause_r562.py",
        "logic_source_sha256": sha256(SRC),
        "replaced_constants_only": ["WINDOW_MAP", "WINDOWS", "ARMS"],
        "window_map_r563": {w: ["C1", "R563B0"] for w in WINS},
        "note": "差异面 = 窗集/快照根 (r563) 与臂名; 分类器 / oracle / 重放工序逐字复用",
    }
    d["candidate"] = "R563 §下轮候选 ④ (w115 单窗 −15 的族级只读定因)"
    json.dump(d, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
