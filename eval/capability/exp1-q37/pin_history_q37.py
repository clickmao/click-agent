#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q37 · 候选④: 投影 pin 的**可比性历史** (机取, 不手抄) —— 遮蔽族扩容 ⇒ 口径断点逐轮登记。

问题 (Q36 下轮候选④): 遮蔽族扩容后, 投影摘要的取值口径变了 ⇒ 新 pin 与旧轮次的 pin **不可直接比**,
但历史值散落在 kpi/附录/测试向量注释里, 读者无法一眼看出「哪几轮之间可比、断点在哪、断因是什么」。

做法 (全部机取):
  * 向量真值 = `face_record_canon.py` 里 `TEST_VECTOR_SHA12` 的**逐修订历史** (git 逐提交取, 不抄字面量);
  * 每修订的轮号 = 同提交下 `projection_rules.json` 的 `round` 字段;
  * 断点声明 = 同提交下 `projection_rules.json` 的 `comparability_break` 是否**较前一修订变化**(有则记断因摘要);
  * 结论: 相邻修订向量相同 ⇒ 可直接比; 不同 ⇒ 断点 (必须重取 pin, 旧读数仅作历史)。

三态: 0 = 报告落盘 / 2 = 前提不成立(取不到两个以上修订, 判据无从成立) / 3 = 环境失败 (git 不可用)。
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CANON = 'eval/capability/face_record_canon.py'
RULES = 'eval/capability/projection_rules.json'
OUT = os.path.join(HERE, 'pin_history_q37.json')
CURRENT_ROUND = 'EXP1-Q37'


def git(*args, text=True):
    p = subprocess.run(['git'] + list(args), cwd=ROOT, capture_output=True, text=text)
    return p.returncode, p.stdout


def show(rev, path):
    rc, out = git('show', '%s:%s' % (rev, path))
    return out if rc == 0 else None


def vector_of(src):
    m = re.search(r'TEST_VECTOR_SHA12\s*=\s*[\'"]([0-9a-f]{12})[\'"]', src or '')
    return m.group(1) if m else None


def main():
    rc, out = git('log', '--format=%H\t%h\t%ad\t%s', '--date=short', '--', CANON)
    if rc != 0 or not out.strip():
        print('ENV_FAIL: git log 不可用')
        return 3
    revs = [l.split('\t') for l in out.strip().splitlines()]
    rows = []
    for full, short, date, subject in revs:
        v = vector_of(show(full, CANON))
        rules_src = show(full, RULES)
        rnd, brk = None, None
        if rules_src:
            try:
                d = json.loads(rules_src)
                rnd = d.get('round')
                brk = (d.get('comparability_break') or '')[:160] or None
            except Exception:
                pass
        rows.append({'commit': short, 'date': date, 'subject': subject[:70],
                     'vector_sha12': v, 'rules_round': rnd,
                     'comparability_break_declared': bool(brk), 'break_head': brk})
    rows = rows[::-1]                      # 旧 → 新
    for r in rows:
        r['pre_vector_era'] = (r['vector_sha12'] is None)   # 向量机制引入前的修订: 无向量可比
    withv = [r for r in rows if r['vector_sha12']]
    for r in rows:
        i = withv.index(r) if r in withv else None
        prev = withv[i - 1] if (i is not None and i > 0) else None
        r['comparable_with_prev'] = bool(prev and prev['vector_sha12'] == r['vector_sha12'])
    breaks = [{'commit': r['commit'], 'round': r['rules_round'],
               'vec_before': withv[i - 1]['vector_sha12'], 'vec_after': r['vector_sha12'],
               'declared': r['comparability_break_declared'], 'note': r['break_head']}
              for i, r in enumerate(withv) if i and not r['comparable_with_prev']]
    # 本轮 (Q37) 是否改了投影规则? 由工作区 vs HEAD 的规则文件 + 向量一致性判定
    head_rules = show('HEAD', RULES)
    head_vec = vector_of(show('HEAD', CANON))
    wt_vec = vector_of(open(os.path.join(ROOT, CANON), encoding='utf-8').read())
    wt_rules_changed = (head_rules != open(os.path.join(ROOT, RULES), encoding='utf-8').read())
    payload = {
        'round': CURRENT_ROUND, 'schema': 'pin-projections-history/1',
        'truth_sources': {'vector': '%s :: TEST_VECTOR_SHA12' % CANON,
                          'round_and_break': '%s (round / comparability_break)' % RULES,
                          'method': 'git show 逐修订 (旧→新), 不抄字面量'},
        'revisions': rows, 'breaks': breaks,
        'current': {'head_vector': head_vec, 'worktree_vector': wt_vec,
                    'rules_file_changed_vs_head': bool(wt_rules_changed),
                    'comparable_with_previous_round': bool(not wt_rules_changed)},
        'reading': ('Q37 未改投影规则 ⇒ 本轮 pin 与 EXP1-Q36 的 pin **可比**; '
                    '与 EXP1-Q35 及以前**不可比** (断点见 breaks)。'
                    if not wt_rules_changed else
                    'Q37 改了投影规则 ⇒ 与所有历史 pin 不可比 (断点已新增)。'),
    }
    ok = len(withv) >= 2 and all(r['vector_sha12'] for r in withv)   # 前提: ≥2 个有向量的修订
    payload['n_revisions_with_vector'] = len(withv)
    payload['pre_vector_era_revisions'] = [r['commit'] for r in rows if r['pre_vector_era']]
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    print('PIN-HISTORY revisions=%d vectors=%s breaks=%d'
          % (len(rows), [r['vector_sha12'] for r in rows], len(breaks)))
    for b in breaks:
        print('  BREAK %s (%s) %s -> %s declared=%s' % (b['commit'], b['round'], b['vec_before'],
                                                        b['vec_after'], b['declared']))
    print('CURRENT head=%s worktree=%s rules_changed=%s comparable_with_prev_round=%s'
          % (head_vec, wt_vec, wt_rules_changed, payload['current']['comparable_with_previous_round']))
    print('VERDICT=%s out=%s' % ('PASS' if ok else 'FAIL', OUT))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
