#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 候选③ 收口: 未派生器具行的**分类普查** (机检, 不留「我知道有几条但要等下一轮」的账)。

对每条产品面证据行重算 derive(): `instrument is None` 的行按 **cmd 形态**归类原因:
  tmp_instrument   —— 声明的器具落在 /tmp (证据今天不可复现, L1 级缺口)
  shell_assertion  —— 纯 shell 断言链 (无脚本产物, 属设计: 存在性/不存在性核验)
  doc_evidence     —— 证据本体是 .md (人工/文档面)
  directory_evidence —— 证据本体是目录 (多脚本聚合)
  csproj_only      —— 命令只出现 .csproj (无法派生到具体源文件)
  manual_read      —— python3 -c 一次性读取表达式 (无器具)
输出: eval/capability/exp1-q30/instrument_gap_census_q30.json (含逐行 id/原因/证据路径) + stdout 汇总。
"""
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
OUT = os.path.join(ROOT, 'eval/capability/exp1-q30/instrument_gap_census_q30.json')
sys.path.insert(0, os.path.join(ROOT, 'eval/capability'))
import bind_evidence as be  # noqa: E402


def classify(cmd, ep):
    c = cmd or ''
    if '/tmp/' in c:
        return 'tmp_instrument'
    if ep.endswith('.md'):
        return 'doc_evidence'
    if os.path.isdir(os.path.join(ROOT, ep)):
        return 'directory_evidence'
    if c.startswith('test ') or ' test ! ' in c or '! grep' in c:
        return 'shell_assertion'
    if '.csproj' in c and '.cs' not in c:
        return 'csproj_only'
    if 'python3 -c' in c or 'python -c' in c:
        return 'manual_read'
    return 'other'


def main():
    reg = json.load(open(os.path.join(ROOT, 'docs/verification-registry.json'), encoding='utf-8'))
    rows = reg['rows']
    tracked, dirty = be.git_state(ROOT)
    gaps, derived_n = [], 0
    for r in rows:
        if not be.needs_field(r):
            continue
        f = be.derive(ROOT, r, tracked, dirty)
        if f.get('instrument'):
            derived_n += 1
            continue
        gaps.append({'id': r.get('id'), 'reason_class': classify(r.get('evidence_cmd'), r.get('evidence_path', '')),
                     'evidence_path': r.get('evidence_path'), 'level': r.get('level'),
                     'cmd_head': (r.get('evidence_cmd') or '')[:110]})
    by = {}
    for g in gaps:
        by[g['reason_class']] = by.get(g['reason_class'], 0) + 1
    rep = {'round': 'EXP1-Q30', 'rows_covered': derived_n + len(gaps), 'derived_instrument': derived_n,
           'no_instrument': len(gaps), 'by_reason_class': by, 'gaps': gaps}
    open(OUT, 'w', encoding='utf-8').write(json.dumps(rep, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'derived_instrument': derived_n, 'no_instrument': len(gaps), 'by_reason_class': by},
                     ensure_ascii=False))
    for g in gaps:
        print('  %-52s %-18s %s' % (g['id'], g['reason_class'], g['evidence_path']))
    print('落盘', os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
