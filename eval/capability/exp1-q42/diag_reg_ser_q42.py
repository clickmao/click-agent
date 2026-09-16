#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q42 · 诊断: 登记表「序列化器逐字节复现」为何 FAIL (禁重排, 先定位分歧点)。"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
REG = ROOT / 'docs' / 'verification-registry.json'
raw = REG.read_text(encoding='utf-8')
doc = json.loads(raw)
repro = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
print('len_raw=%d len_repro=%d' % (len(raw), len(repro)))
n = min(len(raw), len(repro))
i = next((k for k in range(n) if raw[k] != repro[k]), None)
print('first_diff_byte=%s' % i)
if i is not None:
    ls = raw[:i].count('\n') + 1
    print('first_diff_line=%d' % ls)
    print('raw   : %r' % raw[max(0, i - 60):i + 60])
    print('repro : %r' % repro[max(0, i - 60):i + 60])
print('tail_raw=%r' % raw[-6:])
print('raw_lines=%d repro_lines=%d' % (raw.count('\n'), repro.count('\n')))
# 逐行比对 (定位所有形态差异, 只报前 8 处)
import difflib
rl, pl = raw.splitlines(True), repro.splitlines(True)
diffs = list(difflib.unified_diff(rl, pl, 'disk', 'repro', n=0))
print('diff_hunks=%d' % sum(1 for l in diffs if l.startswith('@@')))
for l in diffs[:24]:
    print('  ' + l.rstrip()[:150])
