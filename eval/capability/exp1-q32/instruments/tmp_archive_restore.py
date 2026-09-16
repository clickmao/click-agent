#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q32 · C1 自足入口: 归档件 → /tmp 目标路径的**逐位还原 (materialize)**。

回答 AF.7 候选①的裁定问题「是否允许给归档件加注入开关」:
  · **不允许**改归档件字节 (sha256 pin 即证据, 见 prereg r3/D-ARCH);
  · 正解 = 在**入口层**把归档副本还原到归档件硬编码的路径 (单向下行, 逐位校验), 冲突即 fail-closed。

命令:
  --check     (默认): 归档件存在 + sha256 与 manifest 相符; 报告 /tmp 目标状态 (identical/absent/divergent)。
  --restore   : absent ⇒ 复制归档件到目标 (逐位复核); identical ⇒ no-op (不动 mtime); divergent ⇒ rc=2 拒绝覆盖。
  --only NAME : 限定条目 (可多次)。
  --group NAME : 限定**条目组** (如 r391probe; 一个来源目录由多个文件构成时用组, 可多次)。
  --restore-to DIR : 覆盖目标目录 (仅测试/夹具用)。
  --selftest  : 三态夹具 (absent / identical / divergent) ⇒ 期望 restore / noop / refuse。
退出码: 0 通过 / 2 断言失败 (divergent 或 sha 不符) / 3 环境失败 (manifest/归档件缺失)。
"""
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
MANIFEST = 'eval/capability/exp1-q32/archived_tmp/manifest.json'


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def restore_one(entry, dst, dry=False):
    """返回 (verdict, rc)。dst = 目标路径。"""
    src = os.path.join(ROOT, entry['archive'])
    if not os.path.isfile(src):
        return 'archive_missing', 3
    if sha256(src) != entry['sha256']:
        return 'archive_sha_mismatch', 2
    if not os.path.exists(dst):
        if dry:
            return 'would_restore', 0
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        if sha256(dst) != entry['sha256']:
            os.remove(dst)
            return 'restore_mismatch', 2
        return 'restored', 0
    if sha256(dst) == entry['sha256']:
        return 'identical_noop', 0
    return 'REFUSE_divergent', 2


def selftest():
    bad = 0
    tmp = tempfile.mkdtemp(prefix='q32-mat-')
    try:
        body = b'#!/bin/sh\necho hi\n'
        arc = os.path.join(tmp, 'arc.sh')
        open(arc, 'wb').write(body)
        entry = {'archive': os.path.relpath(arc, ROOT) if arc.startswith(ROOT) else arc,
                 'sha256': hashlib.sha256(body).hexdigest(), 'name': 'fixture'}
        # 夹具基址改为 tmp (绝对路径可被 os.path.join 原样使用)
        cases = [('absent', None, 'restored', 0),
                 ('identical', body, 'identical_noop', 0),
                 ('divergent', b'other\n', 'REFUSE_divergent', 2)]
        for name, dstbody, want_v, want_rc in cases:
            dst = os.path.join(tmp, 'dst_%s.sh' % name)
            if dstbody is not None:
                open(dst, 'wb').write(dstbody)
            v, rc = restore_one(entry, dst)
            ok = (v == want_v and rc == want_rc)
            bad += 0 if ok else 1
            print('  %-10s expect=%s/%d got=%s/%d %s' % (name, want_v, want_rc, v, rc, 'OK' if ok else 'FAIL'))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('SELFTEST %s (%d/%d)' % ('PASS' if bad == 0 else 'FAIL', 3 - bad, 3))
    return 0 if bad == 0 else 2


def main():
    if '--selftest' in sys.argv:
        return selftest()
    mp = os.path.join(ROOT, MANIFEST)
    if not os.path.isfile(mp):
        print('ENV_FAIL: manifest 缺失 %s' % MANIFEST)
        return 3
    man = json.load(open(mp, encoding='utf-8'))
    only = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--only' and i + 1 < len(sys.argv)]
    groups = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--group' and i + 1 < len(sys.argv)]
    alt_base = None
    if '--restore-to' in sys.argv:
        alt_base = sys.argv[sys.argv.index('--restore-to') + 1]
    entries = [e for e in man['entries'] if e['kind'] == 'copy'
               and (not only or e['name'] in only) and (not groups or e.get('group') in groups)]
    if not entries:
        print('ENV_FAIL: --only/--group 过滤后无条目')
        return 3
    do_restore = '--restore' in sys.argv
    rc, rows = 0, []
    for e in entries:
        dst = os.path.join(alt_base, os.path.basename(e['origin'])) if alt_base else e['origin']
        if do_restore:
            v, r = restore_one(e, dst)
        else:
            src = os.path.join(ROOT, e['archive'])
            if not os.path.isfile(src):
                v, r = 'archive_missing', 3
            elif sha256(src) != e['sha256']:
                v, r = 'archive_sha_mismatch', 2
            elif not os.path.exists(dst):
                v, r = 'target_absent', 3
            else:
                v, r = ('target_identical' if sha256(dst) == e['sha256'] else 'target_divergent'), \
                       (0 if sha256(dst) == e['sha256'] else 2)
        rc = max(rc, r)
        rows.append({'name': e['name'], 'target': dst, 'verdict': v, 'rc': r})
        print('  %-26s %-18s %s' % (e['name'], v, dst))
    print('MODE=%s n=%d %s' % ('restore' if do_restore else 'check', len(rows),
                               'MATERIALIZE=%s' % ('FAIL' if rc == 2 else ('ABSTAIN' if rc == 3 else 'OK'))))
    return rc


if __name__ == '__main__':
    sys.exit(main())
