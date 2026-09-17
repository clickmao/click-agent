#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q36 器具 2/2: 补齐 trace 扫描派生量族 (整族为窗口环境量) —— 幂等 + 逐字节复现闸。

依据 (实测): 投影后同树态重跑仍差 `trace/raw_events` (6158→6159) 与 `trace/raw_paths_n`
(3104→3105) —— 扫描到的原始事件/路径条数随窗口内 .git 与临时文件变化, 属环境族;
`trace/commands` / `trace/events` 在跨树态对照 (T3 vs T4 59→60) 亦变。四者同为扫描派生量。
"""
import json
import sys

RULE = 'eval/capability/projection_rules.json'
ROUND = 'EXP1-Q36'
raw = open(RULE, 'rb').read().decode('utf-8')
doc = json.loads(raw)


def ser(d):
    return json.dumps(d, ensure_ascii=False, indent=1) + '\n'


print('ROUNDTRIP_IDENTICAL=%s' % (ser(doc) == raw))
if ser(doc) != raw:
    sys.exit(2)

add = [
    {"path": "side_effect_attribution/trace/commands", "mode": "scalar",
     "basis": "EXP1-Q36 实测 (T3 vs T4 59→60): 扫描子进程数, 随窗口内容变化。"},
    {"path": "side_effect_attribution/trace/events", "mode": "scalar",
     "basis": "EXP1-Q36: 同上 (events 是 commands 的派生量)。"},
    {"path": "side_effect_attribution/trace/raw_events", "mode": "scalar",
     "basis": "EXP1-Q36 实测 (T4 vs T5 6158→6159, 同树态): 原始事件条数随窗口内 .git/临时文件变化。"},
    {"path": "side_effect_attribution/trace/raw_paths_n", "mode": "scalar",
     "basis": "EXP1-Q36 实测 (T4 vs T5 3104→3105, 同树态): 原始路径去重条数, 同上。"},
]
have = {r['path'] for r in doc['rules']}
n_before = len(doc['rules'])
for a in add:
    if a['path'] in have:
        print('IDEMPOTENT: %s' % a['path'])
        continue
    doc['rules'].append(a)
doc['round'] = ROUND
doc['owner_round'] = ROUND
doc['note'] = doc['note'] + (' EXP1-Q36: 新增 drop / drop_by_id 两模式 (整子树含基数剔除 / 成员级按身份'
                             '选择性遮蔽) 并补齐 trace 扫描派生量族; 不动点宣称的**前置条件**见 '
                             'clean_window_condition。')
out = ser(doc)
open(RULE, 'w', encoding='utf-8', newline='').write(out)
back = json.loads(open(RULE, encoding='utf-8').read())
print('RULES %d -> %d' % (n_before, len(back['rules'])))
assert len(back['rules']) == n_before + len(add)
print('READBACK_OK')
