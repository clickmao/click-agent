#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q37 · 候选①: `l2.instruments-check` 偶发 rc=1 的**隔离复跑分诊** (机取, 不手抄)。

背景 (EXP1-Q36 kpi 边界②): T8 与 T9 同树态, 但 results/16 `l2.instruments-check` rc 0→1
(墙钟 202.14s → 273.88s)。本轮把「该红是真回归还是同机争用假红」判到底。

预注册 (写于取证前, 本文件即判据载体):
  P1 分诊三态: `REGRESSION` (隔离复跑仍红) / `CONTENTION_FALSE_RED` (隔离复跑转绿 ∧ 有并发体在场证据)
     / `ABSTAIN` (证据不足, 不猜)。
  P2 取证面 (全部机取, 每条带来源路径):
     s1 T9 面记录里该行的 rc/pass;
     s2 T9 内层 (嵌套 scoped) 记录的 rc/substr_ok/measurement_ok/self_dirt ⇒ 区分「断言红」vs「弃权」;
     s3 同一命令的**隔离复跑**读数 (exit_code + C13 夹具 + C14 明细);
     s4 该窗口内的并发写者证据 (src/**/*.cs mtime 落点 + 面记录 census 里的构建进程);
     s5 面自身判据里**唯一**与同机负载耦合的检查项 (由器具源码机取: C14 的 mtime 扫描面)。
  P3 机理判据: 若 s2 为「断言红」(rc=2, measurement_ok=True, 无弃权) ∧ s5 唯一 ∧ s4 非空
     ⇒ 判 `CONTENTION_FALSE_RED`; 若 s3 仍红 ⇒ 判 `REGRESSION`。
  P4 证据档位: 只凭本文件 = L2 (机理 + 既有记录); 叠加 s3 隔离复跑转绿 = L3。
     不够 L3 的部分必须显式写 `not_recoverable` (不冒充)。
  P5 fail-closed: 任一面文件缺失/字段缺失 ⇒ 该条记 `missing`, 判决落 `ABSTAIN` (不静默跳过)。
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CAP = os.path.join(ROOT, 'eval', 'capability')
EV = os.path.join(HERE, 'evidence')
OUT = os.path.join(HERE, 'triage_q36_t9_rc1.json')

T9_REC = os.path.join(EV, 'face_t9_record.json')
SCOPED = os.path.join(EV, 'scoped_record_19-13-02.json')
Q17_VERDICT = os.path.join(CAP, 'exp1-q20', 'l2runs', 'verdict_q17.json')
INSTR = os.path.join(CAP, 'exp1-q17', 'archive_field_provenance.py')
TARGET = 'l2.instruments-check'
INNER = 'exp1q17.archive-field-provenance'


def jload(p):
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


def mtimes_in_window(lo, hi, pat='*.cs', sub='src'):
    """归因证据 s4: 窗口内被写的源/构建产物 .cs (机取 mtime, 不靠印象)。"""
    out = []
    for dirpath, _dn, fns in os.walk(os.path.join(ROOT, sub)):
        for fn in fns:
            if not fn.endswith('.cs'):
                continue
            p = os.path.join(dirpath, fn)
            try:
                m = os.path.getmtime(p)
            except OSError:
                continue
            if lo <= m <= hi:
                out.append({'path': os.path.relpath(p, ROOT), 'mtime': m})
    return sorted(out, key=lambda d: d['mtime'])


def load_src_criterion():
    """s5: 从器具源码机取 C14 的判据面 (扫描根/glob/阈值) —— 不抄注释。"""
    src = open(INSTR, encoding='utf-8').read()
    m = re.search(r'for pat in \(([^)]*)\)', src)
    globs = re.findall(r'"([^"]+)"', m.group(1)) if m else []
    m2 = re.search(r'if p\.stat\(\)\.st_mtime > (\w+)', src)
    thr = m2.group(1) if m2 else None
    return {'glob_patterns': globs, 'threshold_var': thr,
            'note': 'C14 判据 = 扫描根下 glob 内文件 mtime > 进程起点 ⇒ passed=False (判据不可放宽)'}


def main():
    tri = {'round': 'EXP1-Q37', 'schema': 'triage/1', 'subject': TARGET,
           'prereg': {'P1': ['REGRESSION', 'CONTENTION_FALSE_RED', 'ABSTAIN'],
                      'P2': ['s1 T9 面行', 's2 内层记录', 's3 隔离复跑', 's4 并发写者', 's5 唯一负载耦合判据'],
                      'P4': 'L2=机理+既有记录; L3=叠加隔离复跑转绿',
                      'P5': '缺文件/缺字段 ⇒ missing + ABSTAIN'},
           'evidence': {}, 'verdict': None, 'not_recoverable': []}

    # ---- s1: T9 面行
    s1 = {'source': os.path.relpath(T9_REC, ROOT)}
    try:
        t9 = jload(T9_REC)
        row = [r for r in t9['results'] if r['id'] == TARGET][0]
        sa = t9['side_effect_attribution']
        s1.update({'rc': row['rc'], 'expect_rc': row['expect_rc'], 'pass': row['pass'],
                   'substr_ok': row['substr_ok'], 'l2_ok': row['l2_ok'],
                   'foreign_writes_n': len(sa['foreign_writes']),
                   'census_n': len(sa.get('census_in_repo_cwd', [])),
                   'census_cmds': [c['cmd'][:80] for c in sa.get('census_in_repo_cwd', [])]})
    except Exception as exc:                                  # fail-closed
        s1['missing'] = '%s: %s' % (type(exc).__name__, exc)
        tri['evidence']['s1'] = s1
        tri['verdict'] = 'ABSTAIN'
        json.dump(tri, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('TRIAGE verdict=ABSTAIN (s1 missing)', OUT)
        return 3
    tri['evidence']['s1'] = s1

    # ---- s2: 内层 (嵌套) 记录 ⇒ 断言红 vs 弃权
    s2 = {'source': os.path.relpath(SCOPED, ROOT)}
    try:
        sc = jload(SCOPED)
        inrow = [r for r in sc['results'] if r['id'] == INNER][0]
        sag = sc['side_effect_attribution']
        s2.update({'inner_rc': inrow['rc'], 'inner_pass': inrow['pass'],
                   'inner_substr_ok': inrow['substr_ok'],
                   'face_passed': sc['passed'], 'face_total': sc['total'],
                   'gate_measurement_ok': sag['measurement_ok'],
                   'gate_self_writes': sag['self_writes'],
                   'assertion_red': (inrow['rc'] == inrow['expect_rc'] + 2 and sag['measurement_ok']
                                     and not sag['self_writes']),
                   'mtime': os.path.getmtime(SCOPED)})
    except Exception as exc:
        s2['missing'] = '%s: %s' % (type(exc).__name__, exc)
    tri['evidence']['s2'] = s2

    # ---- s3: 隔离复跑 (同一命令, 无并发构建窗口)
    s3 = {'source': os.path.relpath(Q17_VERDICT, ROOT)}
    try:
        q = jload(Q17_VERDICT)
        red = [c['id'] for c in q['checks'] if not c['passed']]
        fx = q.get('fixtures', [])
        s3.update({'generated': q.get('generated'), 'exit_code': q.get('exit_code'),
                   'checks_red': red, 'fixtures_passed': '%d/%d' % (sum(1 for f in fx if f['passed']), len(fx)),
                   'c14_detail': [c['detail'] for c in q['checks'] if c['id'] == 'C14'][0]
                   if any(c['id'] == 'C14' for c in q['checks']) else None})
    except Exception as exc:
        s3['missing'] = '%s: %s' % (type(exc).__name__, exc)
    tri['evidence']['s3'] = s3

    # ---- s4: 并发写者 (T9 窗口 = 19:11:00 ~ 19:15:30 本地墙钟)
    import datetime
    lo = datetime.datetime(2026, 9, 16, 19, 11, 0).timestamp()
    hi = datetime.datetime(2026, 9, 16, 19, 15, 40).timestamp()
    touched = mtimes_in_window(lo, hi)
    s4 = {'window_local': ['2026-09-16T19:11:00', '2026-09-16T19:15:40'],
          'src_cs_touched_n': len(touched), 'src_cs_touched': touched,
          'builders_in_census': [c for c in s1.get('census_cmds', [])
                                 if 'dotnet' in c or 'publish' in c or 'MSBuild' in c],
          'note': ('窗口内 src/**/*.cs 被写 ⇒ C14 的 mtime 判据在**原理上**必命中; '
                   '构建产出的 obj/*.cs (AssemblyInfo/GlobalUsings) 属同一 glob, 且会被后续构建覆盖 '
                   '⇒ 逐条回溯已不可得 (见 not_recoverable)')}
    tri['evidence']['s4'] = s4
    if s4['src_cs_touched_n'] == 0 and not s4['builders_in_census']:
        tri['not_recoverable'].append('T9 窗口内并发写者证据为空 ⇒ 机理不成立')

    # ---- s5: 唯一负载耦合判据 (源码机取)
    tri['evidence']['s5'] = load_src_criterion()

    # ---- 判决 (预注册 P3)
    inner_red = s2.get('assertion_red') is True
    rerun_green = s3.get('exit_code') == 0 and not s3.get('checks_red')
    contention = inner_red and s4['src_cs_touched_n'] > 0
    if s2.get('missing') or s3.get('missing'):
        tri['verdict'] = 'ABSTAIN'
    elif not rerun_green:
        tri['verdict'] = 'REGRESSION'
    elif contention:
        tri['verdict'] = 'CONTENTION_FALSE_RED'
    else:
        tri['verdict'] = 'ABSTAIN'
    tri['grade'] = 'L3' if tri['verdict'] == 'CONTENTION_FALSE_RED' else 'L2'
    tri['not_recoverable'] += [
        'T9 内层失败的**具体检查项**不可取回: 内层记录只留 rc/substr, 逐检查明细写在器具 --out 文件里, '
        '该文件在 20:17 被同一命令的后续运行覆盖 (mtime=20:17:10), 旧内容无副本',
        'T9 的 strace 原始轨迹目录已不可寻 (sidecar 的 trace_dir 记 <runtime>, /tmp 下已回收)',
    ]
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(tri, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    print('TRIAGE %s verdict=%s grade=%s' % (TARGET, tri['verdict'], tri['grade']))
    print('  s1 rc=%s pass=%s | s2 inner_rc=%s assertion_red=%s | s3 exit=%s red=%s'
          % (s1.get('rc'), s1.get('pass'), s2.get('inner_rc'), s2.get('assertion_red'),
             s3.get('exit_code'), s3.get('checks_red')))
    print('  s4 src .cs touched in window = %d %s'
          % (s4['src_cs_touched_n'], [t['path'] for t in touched][:6]))
    print('  s5 %s' % tri['evidence']['s5'])
    print('  out=%s' % OUT)
    return 0 if tri['verdict'] == 'CONTENTION_FALSE_RED' else 2


if __name__ == '__main__':
    sys.exit(main())
