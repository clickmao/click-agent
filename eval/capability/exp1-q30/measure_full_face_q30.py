#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 候选④ 前置测量: 全量面 (21 器具) 在**归因式副作用闸**下的 trace 体量。

为什么要先测: Q22 引入归因闸后全量面**从未跑过** (committed 读数停在 Q21 口径 17/18, pre-gate)。
首次 scoped 试跑 (3 器具/6 命令) 实测 `log_bytes=17,943,199` > `LOG_SOFT_CAP=8MiB` ⇒ `capped ⇒ 弃权 (rc=3)`。
⇒ 阈值 8MiB 是**scoped 档**标定的, 对全量面结构性过小。本器在内存中抬闸上限 (不改仓库内器具),
只把读数落 scratch ⇒ 由数据定新阈值 (数据先行), 不拍脑袋。

输出: eval/capability/exp1-q30/scratch/full_face_probe.json (面别 = 探针, 不覆盖全量面记录)。
"""
import importlib.util
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
SEG = os.path.join(ROOT, 'eval/capability/exp1-q22/side_effect_gate.py')
IC = os.path.join(ROOT, 'eval/capability/instruments_check.py')
OUT = 'eval/capability/exp1-q30/scratch/full_face_probe.json'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    seg = load('side_effect_gate', SEG)
    print('CAP_BEFORE soft=%d hard=%d' % (seg.LOG_SOFT_CAP, seg.LOG_HARD_CAP))
    seg.LOG_SOFT_CAP = 512 * 1024 * 1024          # 探针期: 只为测体量, 不改库存器具
    seg.LOG_HARD_CAP = 1024 * 1024 * 1024
    sys.modules['side_effect_gate'] = seg          # instruments_check 的 `import side_effect_gate` 复用本实例
    ic = load('instruments_check_probe', IC)
    sys.argv = ['instruments_check.py', '--out', OUT]
    rc = ic.main()
    print('PROBE_RC=%s' % rc)
    return 0


if __name__ == '__main__':
    sys.exit(main())
