#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q36: 器具面清单 (instruments.json) 的 content-sha12 声明同步 —— 逐字节复现闸 + 幂等 + 读回。

为何要: 本轮改了 `face_cap_headroom.py` (轮号参数化) 与 `only_equivalence_guard.py` (反证去饱和)
⇒ 二者 content-sha 变 ⇒ 清单行声明漂移 (面记录会报 L2 DRIFT)。纪律: 器具**定稿之后**一次性同步。
"""
import hashlib
import json

P = 'eval/capability/instruments.json'
raw = open(P, 'rb').read().decode('utf-8')
doc = json.loads(raw)


def ser(d):
    return json.dumps(d, ensure_ascii=False, indent=1) + '\n'


print('ROUNDTRIP_IDENTICAL=%s' % (ser(doc) == raw))
assert ser(doc) == raw, '序列化器不能逐字节复现 ⇒ 拒绝静默重排 (改用文本插入)'


def sha12(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:12]


changed = []
for r in doc['instruments']:
    cmd = r.get('cmd') or ''
    parts = cmd.split()
    cand = [p for p in parts if p.startswith('eval/') and p.endswith('.py')]
    if not cand:
        continue
    path = cand[0]
    if r.get('version_source') != 'content-sha12':
        continue
    actual = sha12(path)
    if r.get('instrument_sha12') != actual:
        changed.append((r['id'], r.get('instrument_sha12'), actual, path))
        r['instrument_sha12'] = actual
        r['version'] = 'content-sha12:%s' % actual

if not changed:
    print('IDEMPOTENT: 无声明漂移')
else:
    doc['round'] = 'EXP1-Q36'
    doc['owner_round'] = 'EXP1-Q36'
    open(P, 'w', encoding='utf-8', newline='').write(ser(doc))
    back = json.loads(open(P, encoding='utf-8').read())
    for rid, old, new, path in changed:
        row = [x for x in back['instruments'] if x['id'] == rid][0]
        print('SYNC %-28s %s -> %s (%s) readback=%s' % (rid, old, new, path,
                                                        'OK' if row['instrument_sha12'] == new else 'MISMATCH'))
        assert row['instrument_sha12'] == new
print('CHANGED=%d' % len(changed))
