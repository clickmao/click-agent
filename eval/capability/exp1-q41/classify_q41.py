#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q41 · H1 的**事后分类** (预注册判据 FAIL 照原样保留; 本节读数标 checks_posthoc)。

H1 原始读数 = 默认作用面历史回放 violations>0 ⇒ 判 FAIL (不改判据)。
本节回答: 这些违规是「契约问世前的旧态」还是「契约生效后仍发生」? —— 只有后者才与
「转正 (默认开) 会不会误拦正常提交」直接相关。

口径修正 (自捕的两处器具缺陷, 见读数 `instrument_defects`):
  D1 首版把违规列表 `viol[:20]` 截断归档 ⇒ 总体被静默缩小 (37→20); 已改全量归档。
  D2 首版用 `--n 1 --skip=1` 取「下一次触碰」—— git log 逆序, skip=1 取到的是**上一次**;
      已改为按 `--reverse` 全序定位 index ∓ 1。

三态退出码: 0 全绿 / 2 判据红 / 3 环境不可判。
"""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONTRACT_SRC = 'eval/capability/bind_evidence.py'


def git(*args, binary=False):
    p = subprocess.run(['git'] + list(args), cwd=str(ROOT), capture_output=True)
    if p.returncode != 0:
        return None
    return p.stdout if binary else p.stdout.decode('utf-8', 'replace')


def epoch(sha):
    v = git('show', '-s', '--format=%ct', sha)
    try:
        return int((v or '').strip())
    except ValueError:
        return 0


def main():
    A = json.loads((HERE / 'replay_q41_scopeA.json').read_text(encoding='utf-8'))
    rows = A['violation_rows']

    # 契约引入点: TAIL_CONTRACT 首次进入 bind_evidence.py 的那次提交 (机取, 不写死 sha)
    intro_log = git('log', '-S', 'TAIL_CONTRACT', '--format=%H %ct', '--', CONTRACT_SRC)
    intro_sha, intro_ct = '', 0
    if intro_log:
        first = [l for l in intro_log.splitlines() if l.strip()][-1]     # 最早一条
        intro_sha, _, c = first.partition(' ')
        intro_ct = int(c or 0)
    head_ct = epoch('HEAD')

    out = {'instrument_defects': ['D1 violation_rows 截断归档 (viol[:20]) ⇒ 总体静默缩小',
                                 'D2 --skip=1 取到的方向与命名相反 (取到上一次触碰)'],
           'contract_intro_commit': intro_sha[:12], 'contract_intro_ct': intro_ct,
           'head_ct': head_ct, 'violations_total': len(rows)}

    order = {}
    per = {}
    for r in rows:
        full = git('rev-parse', r['sha']) or ''
        full = full.strip()
        ct = epoch(full) if full else 0
        path = r['path']
        if path not in order:
            order[path] = [x for x in (git('log', '--reverse', '--format=%H', '--', path) or '').split() if x]
        seq = order[path]
        idx = seq.index(full) if full in seq else -1
        nxt = seq[idx + 1] if 0 <= idx < len(seq) - 1 else None
        prv = seq[idx - 1] if idx > 0 else None

        def tail_lf(sha):
            if not sha:
                return None
            raw = git('show', '%s:%s' % (sha, path), binary=True)
            return None if raw is None else bool(raw.endswith(b'\n'))

        row = {**r, 'full': full[:12], 'ct': ct,
               'phase': 'pre_contract' if (intro_ct and ct < intro_ct) else 'post_contract',
               'prev_tail_lf': tail_lf(prv), 'next_tail_lf': tail_lf(nxt),
               'subject': (git('show', '-s', '--format=%s', full) or '').strip()[:60] if full else ''}
        out.setdefault('rows', []).append(row)
        per.setdefault(full[:12], []).append(row)

    out['rows'] = sorted(out['rows'], key=lambda r: r['ct'])
    out['commits_blocked_if_default_on'] = len(per)
    out['by_phase'] = {'pre_contract': len([r for r in out['rows'] if r['phase'] == 'pre_contract']),
                       'post_contract': len([r for r in out['rows'] if r['phase'] == 'post_contract'])}
    out['post_contract_commits_with_violation'] = len({r['full'] for r in out['rows'] if r['phase'] == 'post_contract'})
    out['why_histogram'] = {}
    for r in out['rows']:
        out['why_histogram'][r['why']] = out['why_histogram'].get(r['why'], 0) + 1
    out['path_histogram'] = {}
    for r in out['rows']:
        out['path_histogram'][r['path']] = out['path_histogram'].get(r['path'], 0) + 1
    # 契约后窗口 (转正直接相关的窗口)
    if intro_ct:
        post_c = [c for c in (git('log', '--since=@%d' % intro_ct, '--format=%H') or '').split() if c]
        out['post_contract_window'] = {'commits_total': len(post_c), 'commits_touch_targets': 0,
                                       'violations': out['by_phase']['post_contract']}
        touched = [c for c in (git('log', '--since=@%d' % intro_ct, '--format=%H', '--',
                                   *A['targets']) or '').split() if c]
        out['post_contract_window']['commits_touch_targets'] = len(touched)
    (HERE / 'replay_q41_scopeA_classified.json').write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    print('CLASSIFY contract_intro=%s (ct=%d)  HEAD_ct=%d' % (out['contract_intro_commit'], intro_ct, head_ct))
    print('CLASSIFY violations=%d  commits_blocked_if_default_on=%d' % (len(rows), len(per)))
    print('CLASSIFY by_phase=%s  why=%s' % (out['by_phase'], out['why_histogram']))
    print('CLASSIFY paths=%s' % out['path_histogram'])
    print('CLASSIFY prev_tail_lf=%s next_tail_lf=%s' % (
        {k: len([r for r in out['rows'] if r['prev_tail_lf'] is k]) for k in (True, False, None)},
        {k: len([r for r in out['rows'] if r['next_tail_lf'] is k]) for k in (True, False, None)}))
    print('CLASSIFY post_contract_window=%s' % out.get('post_contract_window'))
    for r in out['rows'][-5:]:
        print('   %s %s %s why=%s prev=%s next=%s | %s' % (r['full'], r['phase'], r['path'], r['why'],
                                                           r['prev_tail_lf'], r['next_tail_lf'], r['subject']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
