#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q33 · C2: 归档 ripple 收口 —— `deps_tmp_refs` 逐条裁定。

Q32 (§AG.6.6) 只登记了归档件内部引用的 /tmp 依赖 (`manifest.entries[].deps_tmp_refs`), 未逐条带入库
⇒ 归档件在 /tmp 被清空后仍**依赖这些原件**才能真跑。本器具把 22 条 distinct 依赖逐条裁定:

  类 (闭集):
    archived           —— 小文本 (≤256 KiB ∧ 无 NUL) ⇒ **逐字节入库** (sha256 + bytes 双读数)
    external_asset     —— 在场但不宜入库 (目录 / 大文件 / 二进制: 发布物、venv、构建产物)
    runtime_product    —— 不在场且属运行时产物 (日志/断点/临时态), 接受可能缺席
    extractor_truncation —— 不在场且字符串本身是**截断的捕获** (原抽取器截断) ⇒ 不可解析, 明示

判据 (预注册 §criteria.C2): 22/22 有裁定 ∧ 入库者 sha256 与源逐位相同 ∧ 复跑幂等 (noop_identical)
∧ 守恒 (Σ类 == distinct 数)。归档目标已存在但字节不同 ⇒ REFUSE rc=2 (fail-closed)。
退出码: 0 全裁定 / 2 冲突 / 3 环境失败。
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
Q32_MANIFEST = 'eval/capability/exp1-q32/archived_tmp/manifest.json'
ARDIR = 'eval/capability/exp1-q33/archived_deps'
MANIFEST = ARDIR + '/manifest_deps.json'
OUT = 'eval/capability/exp1-q33/deps_adjudication_q33.json'
MAX_ARCHIVE_BYTES = 262144
CLASSES = ('archived', 'external_asset', 'runtime_product', 'extractor_truncation')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha12(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def is_textish(path):
    try:
        with open(path, 'rb') as fh:
            head = fh.read(4096)
    except OSError:
        return False
    return b'\x00' not in head


def dir_stats(path):
    n, nbytes = 0, 0
    for dp, _dn, fn in os.walk(path):
        for f in fn:
            fp = os.path.join(dp, f)
            n += 1
            try:
                nbytes += os.path.getsize(fp)
            except OSError:
                pass
    return n, nbytes


def classify(dep, root=None):
    """返回 (class, payload)。root 可指向夹具根 (selftest 用)。"""
    root = root or ROOT
    full = dep if os.path.isabs(dep) else os.path.join(root, dep)
    if not os.path.exists(full):
        base = os.path.basename(dep.rstrip('/'))
        if base.endswith(('-', '_')) or len(base) < 3:
            return 'extractor_truncation', {'reason': 'basename 是截断片段 (抽取器截断), 不可解析为独立路径',
                                            'basename': base}
        if dep.endswith(('.log', '.jsonl', '.pid')) or '/logs/' in dep:
            return 'runtime_product', {'reason': '不在场且属运行时产物 (日志/断点态) ⇒ 接受缺席'}
        return 'runtime_product', {'reason': '不在场; 未登记为复现前提 ⇒ 接受缺席 (可升级为 external_asset)'}
    if os.path.isdir(full):
        n, nb = dir_stats(full)
        return 'external_asset', {'kind': 'directory', 'n_files': n, 'bytes': nb,
                                  'reason': '目录 (运行时环境 / 发布物) ⇒ 不入库, 记在场读数'}
    size = os.path.getsize(full)
    if size > MAX_ARCHIVE_BYTES or not is_textish(full):
        return 'external_asset', {'kind': 'large_file' if size > MAX_ARCHIVE_BYTES else 'binary_file',
                                  'bytes': size, 'sha256': sha256(full),
                                  'reason': '大文件/二进制 (发布物、构建产物) ⇒ 不入库, 记 sha256 供复现核验'}
    return 'archived', {'bytes': size, 'sha256': sha256(full)}


def archive_one(dep, root=None, apply_=True):
    """把 classified == archived 的依赖逐字节入库; 返回 (verdict, rc)。"""
    root = root or ROOT
    src = dep if os.path.isabs(dep) else os.path.join(root, dep)
    rel = ARDIR + '/' + dep.lstrip('/')
    dst = os.path.join(root, rel)
    ssha, sbytes = sha256(src), os.path.getsize(src)
    if os.path.exists(dst):
        if sha256(dst) != ssha:
            return 'REFUSE_divergent', 2
        return 'noop_identical', 0
    if not apply_:
        return 'would_copy', 0
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    if sha256(dst) != ssha or os.path.getsize(dst) != sbytes:
        os.remove(dst)
        return 'COPY_MISMATCH', 2
    return 'archived_verified', 0


def restore_deps(root=None, apply_=True):
    """入口层自足化: 把入库的依赖逐位还原到 origin 路径 (冲突 fail-closed)。
    与 Q32 入口同判据 (noop_identical / restored / REFUSE_divergent / ENV_FAIL), 但走**本轮的**
    manifest (不同归档根), 故独立实现以免改动 pinned 入口。"""
    root = root or ROOT
    mp = os.path.join(root, MANIFEST)
    if not os.path.exists(mp):
        return 3, []
    rows = []
    for e in json.load(open(mp, encoding='utf-8'))['entries']:
        src = os.path.join(root, e['archive'])
        dst = e['dep'] if os.path.isabs(e['dep']) else os.path.join(root, e['dep'])
        if not os.path.exists(src):
            rows.append({'dep': e['dep'], 'verdict': 'ENV_FAIL_archive_missing', 'rc': 3})
            continue
        if sha256(src) != e['sha256']:
            rows.append({'dep': e['dep'], 'verdict': 'REFUSE_archive_tampered', 'rc': 2})
            continue
        if os.path.exists(dst):
            rows.append({'dep': e['dep'],
                         'verdict': 'noop_identical' if sha256(dst) == e['sha256'] else 'REFUSE_divergent',
                         'rc': 0 if sha256(dst) == e['sha256'] else 2})
            continue
        if not apply_:
            rows.append({'dep': e['dep'], 'verdict': 'would_restore', 'rc': 0})
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        rows.append({'dep': e['dep'],
                     'verdict': 'restored' if sha256(dst) == e['sha256'] else 'RESTORE_MISMATCH',
                     'rc': 0 if sha256(dst) == e['sha256'] else 2})
    return max([r['rc'] for r in rows] or [0]), rows


def selftest():
    """4 例: 小文本 ⇒ 入库逐位一致; 目标分歧 ⇒ REFUSE rc=2; 缺席运行时 ⇒ runtime_product (非红);
    大文件 ⇒ external_asset。"""
    import tempfile
    tmp = tempfile.mkdtemp(prefix='q33-deps-')
    bad = 0
    cases = {}
    try:
        os.makedirs(os.path.join(tmp, 'd'), exist_ok=True)
        small = os.path.join(tmp, 'd', 'report.txt')
        open(small, 'w', encoding='utf-8').write('hello 报告\n')
        big = os.path.join(tmp, 'd', 'host.bin')
        with open(big, 'wb') as fh:
            fh.write(b'\x00' * (MAX_ARCHIVE_BYTES + 16))
        from os.path import join as _j
        dep_small = os.path.relpath(small, tmp).replace(os.sep, '/')
        dep_big = os.path.relpath(big, tmp).replace(os.sep, '/')
        cls, pay = classify(dep_small, root=tmp)
        cases['small_text_is_archived'] = (cls == 'archived' and pay['bytes'] == os.path.getsize(small))
        # 入库 (夹具根 = tmp; ARDIR 相对 root 解析)
        v, rc = archive_one(dep_small, root=tmp)
        dst = os.path.join(tmp, ARDIR + '/' + dep_small.lstrip('/'))
        cases['archive_byte_exact'] = (v == 'archived_verified' and rc == 0 and sha256(dst) == sha256(small))
        v2, rc2 = archive_one(dep_small, root=tmp)
        cases['archive_idempotent_noop'] = (v2 == 'noop_identical' and rc2 == 0)
        open(dst, 'w', encoding='utf-8').write('tampered\n')
        v3, rc3 = archive_one(dep_small, root=tmp)
        cases['divergent_target_refused'] = (v3 == 'REFUSE_divergent' and rc3 == 2)
        cases['missing_runtime_not_red'] = classify('/tmp/whatever/run.log', root=tmp) == ('runtime_product',) or \
            classify('/tmp/whatever/run.log', root=tmp)[0] == 'runtime_product'
        cases['truncated_capture_detected'] = classify('/tmp/x/logs/adapter/side-agent-', root=tmp)[0] == 'extractor_truncation'
        cases['big_file_external'] = classify(dep_big, root=tmp)[0] == 'external_asset'
        for k, v in cases.items():
            print('  %-34s %s' % (k, 'OK' if v else 'FAIL'))
            bad += 0 if v else 1
        n = len(cases)
        print('SELFTEST %s (%d/%d)' % ('PASS' if bad == 0 else 'FAIL', n - bad, n))
        return 0 if bad == 0 else 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if '--selftest' in sys.argv:
        return selftest()
    if '--restore' in sys.argv:
        rc, rows = restore_deps()
        for r in rows:
            print('  %-46s %s' % (r['dep'][:46], r['verdict']))
        n_ok = sum(1 for r in rows if r['verdict'] in ('noop_identical', 'restored'))
        print('RESTORE %d/%d  rc=%d' % (n_ok, len(rows), rc))
        print('DEPS_RESTORE=%s' % ('OK' if rc == 0 and n_ok == len(rows) else 'FAIL'))
        return rc
    check_only = '--check' in sys.argv
    q32 = os.path.join(ROOT, Q32_MANIFEST)
    if not os.path.exists(q32):
        print('ENV_FAIL: Q32 manifest 缺失 %s ⇒ 弃权' % Q32_MANIFEST)
        return 3
    m = json.load(open(q32, encoding='utf-8'))
    owners = {}
    for e in m['entries']:
        for d in e.get('deps_tmp_refs', []):
            owners.setdefault(d, []).append(e['name'])
    rows, rc = [], 0
    for dep, own in sorted(owners.items()):
        cls, pay = classify(dep)
        row = {'dep': dep, 'class': cls, 'referenced_by': own}
        row.update(pay)
        if cls == 'archived' and pay['sha256']:
            v, r = archive_one(dep, apply_=not check_only)
            row['archive'] = (ARDIR + '/' + dep.lstrip('/')) if v in ('archived_verified', 'noop_identical') else None
            row['verdict'] = v
            rc = max(rc, r)
        else:
            row['verdict'] = 'declared_' + cls
        rows.append(row)
    by_class = {}
    for r in rows:
        by_class[r['class']] = by_class.get(r['class'], 0) + 1
    n_archived_ok = sum(1 for r in rows if r.get('verdict') in ('archived_verified', 'noop_identical'))
    manifest = {'round': 'EXP1-Q33', 'schema': 'tmp-deps-manifest/1', 'archived_dir': ARDIR,
                'source_manifest': Q32_MANIFEST, 'n_deps': len(rows),
                'rule': '小文本逐字节入库 + sha256 双读数; 目录/大文件/二进制登记为 external_asset (不入库); '
                        '缺席者按运行时产物/截断捕获明示; 归档件禁改字节 (REFUSE_divergent fail-closed)',
                'entries': [r for r in rows if r.get('archive')]}
    payload = {'round': 'EXP1-Q33', 'schema': 'deps-adjudication/1',
               'source_manifest': Q32_MANIFEST, 'source_manifest_sha12': sha12(open(q32, encoding='utf-8').read()),
               'n_distinct_deps': len(rows), 'by_class': by_class,
               'n_archived_verified': n_archived_ok,
               'n_external_assets': by_class.get('external_asset', 0),
               'rows': rows,
               'conservation': {'sum_by_class': sum(by_class.values()), 'distinct': len(rows),
                                'ok': sum(by_class.values()) == len(rows),
                                'classes_subset_of_closed_set': set(by_class) <= set(CLASSES)}}
    if not check_only:
        os.makedirs(os.path.join(ROOT, ARDIR), exist_ok=True)
        with open(os.path.join(ROOT, MANIFEST), 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n')
        with open(os.path.join(ROOT, OUT), 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
    ok = payload['conservation']['ok'] and payload['conservation']['classes_subset_of_closed_set']
    print('DISTINCT_DEPS=%d by_class=%s' % (len(rows), json.dumps(by_class, ensure_ascii=False)))
    print('ARCHIVED_VERIFIED=%d EXTERNAL=%d' % (n_archived_ok, payload['n_external_assets']))
    for r in rows:
        if r['class'] != 'archived':
            print('  %-20s %-46s %s' % (r['class'], r['dep'][:46], r.get('kind', r.get('reason', ''))))
    print('CONSERVATION=%s' % json.dumps(payload['conservation'], ensure_ascii=False))
    print('落盘 %s + %s' % (OUT, MANIFEST))
    print('DEPS_ADJUDICATE=%s' % ('OK' if (ok and rc == 0) else 'FAIL'))
    return 2 if (rc or not ok) else 0


if __name__ == '__main__':
    sys.exit(main())
