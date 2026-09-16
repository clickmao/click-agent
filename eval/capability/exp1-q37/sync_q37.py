#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q37: 器具清单 (instruments.json) 声明同步 + 成员类声明 (候选③) —— 逐字节复现闸 + 幂等 + 读回。

为何要: 本轮改了 3 个器具文件 (archive_field_provenance.py / instruments_check.py / face_class_count.py
为新文件) 并在清单里为**自指成员**新增 `class: informational` 声明 ⇒
  (a) `instrument_sha12`/`version` 会漂移 (面 L2 判红: DRIFT);
  (b) `input_fingerprint` 里被引器具的 sha12 也会漂移 (同上);
  (c) 成员类声明若不落清单, 面执行器读不到 ⇒ 候选③ 静默不生效。
纪律: 先断言序列化器**逐字节复现**原文件 (否则拒写, 改文本插入); 写后读回校验; 幂等。

用法: python3 eval/capability/exp1-q37/sync_q37.py
"""
import hashlib
import json

P = 'eval/capability/instruments.json'
ROUND = 'EXP1-Q37'
INFO_ROWS = {'bind_evidence.check': 'self-referential-tree-state',
             'bind_evidence.committed-state': 'self-referential-tree-state'}
raw = open(P, encoding='utf-8').read()
doc = json.loads(raw)


def ser(d):
    return json.dumps(d, ensure_ascii=False, indent=1) + '\n'


print('ROUNDTRIP_IDENTICAL=%s' % (ser(doc) == raw))
assert ser(doc) == raw, '序列化器不能逐字节复现 ⇒ 拒绝静默重排 (改用文本插入)'


def sha12(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:12]


changed = []
# (a) 成员类声明 + (b) instrument_sha12/version + (c) input_fingerprint 三条一起走同一次写
for r in doc['instruments']:
    if r['id'] in INFO_ROWS and r.get('class') != 'informational':
        r['class'] = 'informational'
        r['why_informational'] = INFO_ROWS[r['id']]
        changed.append('CLASS %s' % r['id'])
    cmd = r.get('cmd') or ''
    cand = [p for p in cmd.split() if p.startswith('eval/') and p.endswith('.py')]
    if cand and r.get('version_source') == 'content-sha12':
        actual = sha12(cand[0])
        if r.get('instrument_sha12') != actual:
            changed.append('SHA %s %s -> %s (%s)' % (r['id'], r.get('instrument_sha12'), actual, cand[0]))
            r['instrument_sha12'] = actual
            r['version'] = 'content-sha12:%s' % actual
    for fp in (r.get('input_fingerprint') or []):
        try:
            actual = sha12(fp['path'])
        except OSError:
            changed.append('MISSING_INPUT %s %s' % (r['id'], fp['path']))
            continue
        if fp.get('sha12') != actual:
            changed.append('FP %s %s %s -> %s' % (r['id'], fp['path'], fp.get('sha12'), actual))
            fp['sha12'] = actual

if not changed:
    print('IDEMPOTENT: 无声明漂移')
else:
    doc['round'] = ROUND
    doc['owner_round'] = ROUND
    with open(P, 'w', encoding='utf-8', newline='') as fh:
        fh.write(ser(doc))
    back = json.loads(open(P, encoding='utf-8').read())
    for rid, why in INFO_ROWS.items():
        row = [x for x in back['instruments'] if x['id'] == rid][0]
        ok = (row.get('class') == 'informational' and row.get('why_informational') == why)
        print('READBACK %-28s class=%s why=%s %s' % (rid, row.get('class'),
                                                     row.get('why_informational'), 'OK' if ok else 'MISMATCH'))
        assert ok
    for r in back['instruments']:
        cand = [p for p in (r.get('cmd') or '').split() if p.startswith('eval/') and p.endswith('.py')]
        if cand and r.get('version_source') == 'content-sha12':
            assert r['instrument_sha12'] == sha12(cand[0]), 'sha 读回不一致: %s' % r['id']
        for fp in (r.get('input_fingerprint') or []):
            assert fp['sha12'] == sha12(fp['path']), '指纹读回不一致: %s %s' % (r['id'], fp['path'])
    print('READBACK_SHA_ALL_OK')
for c in changed:
    print('CHANGED:', c)
print('CHANGED_N=%d' % len(changed))
