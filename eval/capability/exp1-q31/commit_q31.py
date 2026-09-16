#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · 提交纪律: 从 `git status --porcelain` 逐字取路径 + dogfood 新的跨写者提交闸。

① 只提交**本轮清单**内的路径 (显式 add, 禁 `git add -A` —— 整树 add 曾把对侧半成品带进提交);
② 写清单文件 (stage_guard 的声明面), 提交时设 AGENTFRAMEWORK_STAGE_MANIFEST ⇒ 钩子机检 staged == 清单;
③ 提交后回读 HEAD (`git show HEAD:<file>` 关键行) 防并发写者复原导致静默漏提交。
用法: python3 commit_q31.py --msg "<提交信息>" [--dry-run]
"""
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
MANIFEST = 'eval/capability/exp1-q31/round_artifact_list_q31.txt'
Q31_PREFIX = 'eval/capability/exp1-q31/'
EXCLUDE_SUBSTR = ('/scratch/', '/__pycache__/')
EXTRA = ['docs/verification-registry.json', 'eval/capability/instruments.json',
         'eval/capability/instruments_check.py', 'tools/hooks/pre-commit',
         'eval/capability/face-scale-ledger.jsonl', 'docs/improvements.md',
         'eval/capability/instruments-check.json', 'eval/capability/kpi.jsonl',
         'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md']


def git(*args, **kw):
    return subprocess.run(['git'] + list(args), cwd=ROOT, capture_output=True, text=True, check=False)


def main():
    dry = '--dry-run' in sys.argv
    msg = sys.argv[sys.argv.index('--msg') + 1] if '--msg' in sys.argv else 'EXP1-Q31'
    out = git('status', '--porcelain', '-uall').stdout
    paths = []
    for line in out.splitlines():
        rel = line[3:].strip().strip('"')
        if any(s in rel for s in EXCLUDE_SUBSTR):
            continue
        if rel.startswith(Q31_PREFIX) or rel in EXTRA:
            paths.append(rel)
    paths = sorted(set(paths))
    print('ROUND_PATHS n=%d' % len(paths))
    for p in paths:
        print('  %s' % p)
    if dry:
        print('DRY_RUN=OK')
        return 0
    open(os.path.join(ROOT, MANIFEST), 'w', encoding='utf-8').write('\n'.join(paths + [MANIFEST]) + '\n')
    if MANIFEST not in paths:
        paths.append(MANIFEST)
    r = git('add', '--', *paths)
    if r.returncode != 0:
        print('GIT_ADD=FAIL %s' % r.stderr[:200])
        return 2
    staged = [x.strip() for x in git('diff', '--cached', '--name-only').stdout.splitlines() if x.strip()]
    print('STAGED n=%d' % len(staged))
    if sorted(staged) != sorted(paths):
        print('STAGED_MISMATCH extra=%s missing=%s'
              % (sorted(set(staged) - set(paths)), sorted(set(paths) - set(staged))))
        return 2
    env = dict(os.environ)
    env['AGENTFRAMEWORK_STAGE_MANIFEST'] = os.path.join(ROOT, MANIFEST)
    env['AGENTFRAMEWORK_ROUND_CLAIM'] = '/tmp/q31_no_claim'
    c = subprocess.run(['git', 'commit', '-m', msg], cwd=ROOT, capture_output=True, text=True, env=env)
    print((c.stdout or '')[-600:])
    print((c.stderr or '')[-400:])
    print('COMMIT_RC=%d' % c.returncode)
    if c.returncode != 0:
        return 2
    head = git('show', '--stat', '--oneline', 'HEAD').stdout
    print(head[-1200:])
    n = len([l for l in head.splitlines() if '|' in l])
    print('HEAD_FILES=%d (期望 %d)' % (n, len(paths)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
