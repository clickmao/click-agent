#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q38 · 候选①的**修复件**: 器具声明的重审刷新 (stale declaration → re-audit)。

问题 (T11 全量面实测): 器具清单 `eval/capability/instruments.json` 里两行的**字节声明**停在被编辑
之前的版本 —— 而它们各自的 `evidence_path` 文件已被 Q37 的提交 `c54a26a` 改写:

  row                       declared         live
  l2.instruments-check      eb9d30eb1de0     3ea90e4feea5   (eval/capability/instruments_check.py)
  exp1q31.only-equivalence  f477c8ba8bb4     76fef026ffd9   (…/exp1-q31/instruments/only_equivalence_guard.py)

L2 机检的语义 = 「声明 == 现盘字节」(器具已改 ⇒ 引用它的证据须重审)。故**正确动作是重审并刷新声明**,
不是放宽判据: 判据一字未动, 面在修复前照原样判红 (rc=1, 23/25), 修复后再跑一次得新读数。

重审证据 (本轮):
  * 两行的**行为**判据在 T11 面里全绿: rc == expect_rc ∧ expect_substr 命中 ∧ 负控按声明行为
    (l2.instruments-check nc rc=1; exp1q31.only-equivalence nc rc=0) ⇒ 改版后的器具行为与声明一致。
  * `exp1q31.only-equivalence` 改版前后**同树态**对照 (T10 20:29 vs T11 21:47): 改版前该行 rc=2
    (器具自身判红), 改版后 rc=0 ⇒ 改版是修复, 不是回归。

纪律 (承「登记表程序化改写」铁律):
  D1 改写前断言「序列化器逐字节复现原文件」(indent=1 / ensure_ascii=False / 尾形态), 失败 ⇒ 拒绝写盘;
  D2 只动目标行的 `version` / `instrument_sha12` 两个字段, 不做任何重排;
  D3 幂等: 重跑时 0 处改动;
  D4 写盘后读回比对 + 打印逐行 before/after。
"""
import hashlib
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
MAN = ROOT / 'eval/capability/instruments.json'
TARGETS = ('l2.instruments-check', 'exp1q31.only-equivalence')


def sha12(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:12]


def main():
    raw = MAN.read_text(encoding='utf-8')
    doc = json.loads(raw)
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    tail = '\n' if raw.endswith('\n') else ''
    if ser + tail != raw:
        print('SER_ASSERT=FAIL 序列化器未能逐字节复现原文件 ⇒ 拒绝写盘 (fail-closed)')
        print('  RAWLEN=%d SERLEN=%d tail=%r' % (len(raw), len(ser), tail))
        return 3
    print('SER_ASSERT=OK (indent=1, ensure_ascii=False, tail=%s)' % ('LF' if tail else 'NONE'))

    rows = {e['id']: e for e in doc['instruments']}
    changed = []
    for tid in TARGETS:
        e = rows.get(tid)
        if e is None:
            print('MISSING_ROW=%s (fail-closed)' % tid)
            return 3
        live = sha12(e['evidence_path'])
        before = (e.get('version'), e.get('instrument_sha12'))
        if e.get('version_source') != 'content-sha12':
            print('ROW %s: version_source=%r ≠ content-sha12 ⇒ 本件不改 (非本面口径)'
                  % (tid, e.get('version_source')))
            continue
        if before == ('content-sha12:' + live, live):
            print('ROW %-26s UNCHANGED (声明已与现盘一致)' % tid)
            continue
        e['version'] = 'content-sha12:' + live
        e['instrument_sha12'] = live
        changed.append((tid, e['evidence_path'], before, ('content-sha12:' + live, live)))

    if not changed:
        print('IDEMPOTENT=OK (0 处改动, 无需写盘)')
        return 0

    out = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    with open(MAN, 'w', encoding='utf-8', newline='') as fh:
        fh.write(out)
    with open(MAN, encoding='utf-8', newline='') as fh:
        back = fh.read()
    print('WRITE_READBACK=%s' % ('OK' if back == out else 'MISMATCH'))
    if back != out:
        return 2
    print('RE_AUDITED=%d' % len(changed))
    for tid, ep, before, after in changed:
        print('  %-26s %s' % (tid, ep))
        print('     before version=%s instrument_sha12=%s' % before)
        print('     after  version=%s instrument_sha12=%s' % after)
    print('VERDICT=PASS (声明重审刷新完成; 判据未放宽 —— 修复前读数照原样留在 T11)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
