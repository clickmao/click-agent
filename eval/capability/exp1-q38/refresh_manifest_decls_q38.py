#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q38 候选①的修复件 —— **已升格为常设工具** `eval/capability/decl_sweep.py` (EXP1-Q39 候选③)。

本文件保留为**委托 shim**: 让 Q38 的证据命令/证据路径仍可逐字复跑 (证据可复现性), 同时全仓只有
**一份**实现 (无副本漂移)。行为、stdout 机读行 (`DECL_SWEEP checked=/drifted=`) 与退出码
(0 绿 / 2 漂移 / 3 序列化器不复现) 均由 decl_sweep 提供, 与 Q38 件同口径。
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location('decl_sweep', str(ROOT / 'eval/capability/decl_sweep.py'))
ds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ds)

if __name__ == '__main__':
    sys.exit(ds.main())
