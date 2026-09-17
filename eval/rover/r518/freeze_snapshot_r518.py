#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R518 冻结器入口 —— 复用 R513 冻结器本体 (同一权威, 禁分叉), 只把 HERE 指到 r518。

为什么不分叉拷贝: 拷贝 = 两份会漂移的权威。本器 import 原模块后覆写其 HERE/OUT 常量再调用 main(),
冻结逻辑 (逐字节拷树 + sha256 读回 + 窗口件合并语义) 仍只有一处实现。
"""
from __future__ import annotations

import importlib.util
import os
import sys

REPO = "/home/agentuser/AgentFramework"
SRC = os.path.join(REPO, "eval/rover/r513/freeze_snapshot_r513.py")
HERE = os.path.join(REPO, "eval/rover/r518")


def main() -> int:
    spec = importlib.util.spec_from_file_location("freeze_r513_body", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.HERE = HERE                 # 冻结落点改到 r518 (权威代码不变)
    sys.argv = [SRC] + sys.argv[1:]
    return mod.main()


if __name__ == "__main__":
    sys.exit(main())
