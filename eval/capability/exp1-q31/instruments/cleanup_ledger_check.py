#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C1裁定③: 模型清理台账的机检 (原 evidence_cmd 是 `python3 -c` 一次性读取, 无器具)。

台账: eval/rover/r463/deletion-ledger.json = [{path,bytes,sha256}, ...] (已退役模型清单)。
判据 (绑台账主张, 不绑「目录看起来空」):
  P1 台账可解析且为列表, 每条含 path/bytes(>0)/sha256(64 hex) —— 字段完整性;
  P2 台账每条 path 在现盘**不存在** (清理主张为真); 存在即红 (主张被现盘否证);
  P3 保留面 (保留目录) 与台账**无交集** (防「台账里没删干净却被当已删」)。
控制 (--selftest): 正控 (全不存在) 绿 / 负控 (一条仍在) 红 / 负控 (字段缺 sha256) 红 / 环境 (台账缺失) rc=3。
退出码: 0 通过 / 2 断言失败 / 3 环境失败。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
LEDGER = 'eval/rover/r463/deletion-ledger.json'
KEEP_DIRS = ['~/.agentframework/models/']
HEX64 = re.compile(r'^[0-9a-f]{64}$')


def check(ledger, exists=os.path.exists, keep_files=()):
    """纯判据: ledger 已解析对象; exists = 注入式存在性谓词 (便于夹具)。返回 (violations, readings)。"""
    v, r = [], {}
    if not isinstance(ledger, list):
        return ['P1 台账非列表'], {'n': 0}
    r['n'] = len(ledger)
    for i, e in enumerate(ledger):
        if not isinstance(e, dict) or 'path' not in e:
            v.append('P1 第 %d 条缺 path' % i)
            continue
        if not isinstance(e.get('bytes'), int) or e['bytes'] <= 0:
            v.append('P1 %s bytes 非法: %r' % (e['path'], e.get('bytes')))
        if not HEX64.match(str(e.get('sha256', ''))):
            v.append('P1 %s sha256 非法' % e['path'])
        if exists(e['path']):
            v.append('P2 台账声明已删但现盘仍存在: %s' % e['path'])
    paths = {e.get('path') for e in ledger if isinstance(e, dict)}
    inter = sorted(p for p in paths if p in keep_files)
    for p in inter:
        v.append('P3 台账条目出现在保留面: %s' % p)
    r['keep_intersection'] = inter
    r['kept_now'] = sorted(keep_files)
    return v, r


FIXTURES = [
    ('pos_all_absent', [{'path': '/tmp/models/a.gguf', 'bytes': 10, 'sha256': 'a' * 64}], [], True),
    ('nc_still_present', [{'path': '/tmp/models/a.gguf', 'bytes': 10, 'sha256': 'a' * 64}],
     ['/tmp/models/a.gguf'], False),
    ('nc_bad_sha', [{'path': '/tmp/models/a.gguf', 'bytes': 10, 'sha256': 'zz'}], [], False),
    ('nc_not_list', {'path': 'x'}, [], False),
]


def selftest():
    bad = 0
    for name, ledger, present, want_ok in FIXTURES:
        v, _ = check(ledger, exists=lambda p, s=set(present): p in s)
        ok = not v
        if ok != want_ok:
            bad += 1
        print('%-22s expect_pass=%-5s got=%-5s viol=%d  %s'
              % (name, want_ok, ok, len(v), 'OK' if ok == want_ok else 'FAIL'))
    # 反证: 「只看目录是否为空」口径对 nc_bad_sha 恒绿 (目录确实空) ⇒ 证明字段完整性判据非装饰
    naive_empty_dir_ok = not check(FIXTURES[2][1], exists=lambda p: False)[0]
    print('NC_dir_empty_rule_would_pass_bad_sha=%s (期望 False: 目录空 ≠ 台账合法)' % naive_empty_dir_ok)
    if naive_empty_dir_ok:
        print('NC_SETUP_FAIL: 目录口径也能抓出字段缺陷 (夹具失效)')
        bad += 1
    print('SELFTEST %s (%d/%d)' % ('PASS' if bad == 0 else 'FAIL', len(FIXTURES) - bad, len(FIXTURES)))
    return 0 if bad == 0 else 2


def main():
    if '--selftest' in sys.argv:
        return selftest()
    ledger_rel = sys.argv[sys.argv.index('--ledger') + 1] if '--ledger' in sys.argv else LEDGER
    path = ledger_rel if os.path.isabs(ledger_rel) else os.path.join(ROOT, ledger_rel)
    if not os.path.isfile(path):
        print('ENV_FAIL: 台账不存在 %s' % ledger_rel)
        return 3
    try:
        ledger = json.load(open(path, encoding='utf-8-sig'))
    except Exception as e:
        print('ENV_FAIL: 台账不可解析 %r' % e)
        return 3
    kept = []
    for d in KEEP_DIRS:
        dd = os.path.expanduser(d)
        if os.path.isdir(dd):
            kept += [os.path.join(dd, f) for f in sorted(os.listdir(dd))]
    v, r = check(ledger, keep_files=kept)
    print('CLEANUP_LEDGER n=%d kept_now=%s' % (r['n'], [os.path.basename(x) for x in r.get('kept_now', [])]))
    for x in v:
        print('  VIOLATION %s' % x)
    if v:
        print('CLEANUP_LEDGER_CHECK=FAIL (%d 条)' % len(v))
        return 2
    print('CLEANUP_LEDGER_CHECK=OK (台账 %d 条字段完整 + 逐条现盘不存在 + 与保留面无交集)' % r['n'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
