#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q32 · C3 收口: L2 器具面 (instruments.json) 的 pin 重审 —— 器具改后同步 pin。

触发 = 本轮机检实证: 改了 `tools/hooks/pre-commit` (新增 Q32 重审闸) 后, 全量面 26/27 (唯一红 =
`hooks.pre-commit` 的 instrument_sha12 DRIFT) ⇒ 该面只在**跑完全量面**之后才看得见, 已由
`reaudit_guard.py` 前移到提交面 (本脚本即其处置动作)。

纪律: 序列化器逐字节复现断言 → 逐条 sha12 机检 → 只改 `version`/`instrument_sha12` → 幂等 → 读回。
退出码: 0 通过 (含幂等) / 2 断言失败 / 3 环境失败。
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
MAN = 'eval/capability/instruments.json'
# (artifactId, 期望现盘 sha12) —— 现盘值由本脚本重算, 这里只声明「要审的 id」; 空 = 全表按现盘对齐
TARGETS = ['hooks.pre-commit']


def sha12(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()[:12]


def main():
    dry = '--dry-run' in sys.argv
    raw = open(os.path.join(ROOT, MAN), encoding='utf-8', newline='').read()
    doc = json.loads(raw)
    tail = '\n' if raw.endswith('\n') else ''
    if json.dumps(doc, ensure_ascii=False, indent=1) + tail != raw:
        print('SER_ASSERT=FAIL (序列化器不能逐字节复现 ⇒ 拒写)')
        return 3
    print('SER_ASSERT=OK')
    changed, missing = [], []
    for e in doc['instruments']:
        if TARGETS and e.get('id') not in TARGETS:
            continue
        ep = e.get('evidence_path')
        if not ep or not os.path.isfile(os.path.join(ROOT, ep)):
            missing.append(e.get('id'))
            continue
        now = sha12(os.path.join(ROOT, ep))
        if e.get('instrument_sha12') == now:
            print('  %-26s pin 已是最新 (%s)' % (e['id'], now))
            continue
        print('  %-26s REPIN %s → %s' % (e['id'], e.get('instrument_sha12'), now))
        e['instrument_sha12'] = now
        if str(e.get('version', '')).startswith('content-sha12:'):
            e['version'] = 'content-sha12:%s' % now
        changed.append(e['id'])
    if missing:
        print('ENV_FAIL: 目标器具缺 evidence_path: %s' % missing)
        return 3
    if not changed:
        print('IDEMPOTENT=OK (无变化)')
        return 0
    if dry:
        print('DRY_RUN=OK (%d 条待改, 未写盘)' % len(changed))
        return 0
    out = json.dumps(doc, ensure_ascii=False, indent=1) + '\n'
    open(os.path.join(ROOT, MAN), 'w', encoding='utf-8', newline='').write(out)
    back = open(os.path.join(ROOT, MAN), encoding='utf-8', newline='').read()
    print('WRITE_READBACK=%s' % ('OK' if back == out else 'MISMATCH'))
    if back != out:
        return 2
    d2 = json.loads(back)
    print('ENTRY_CONSERVATION=%s (%d 条)' % ('OK' if len(d2['instruments']) == len(doc['instruments'])
                                              else 'FAIL', len(d2['instruments'])))
    bad = [e['id'] for e in d2['instruments'] if e.get('id') in changed
           and e.get('instrument_sha12') != sha12(os.path.join(ROOT, e['evidence_path']))]
    print('POST_PIN=%s %s' % ('OK' if not bad else 'FAIL', bad if bad else '重审后 pin == 现盘 (逐条)'))
    print('REPINNED=%d %s' % (len(changed), changed))
    print(subprocess.run(['git', 'diff', '--numstat', '--', MAN], cwd=ROOT, capture_output=True,
                         text=True).stdout.strip())
    return 0 if not bad else 2


if __name__ == '__main__':
    sys.exit(main())
