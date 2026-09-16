#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q32 · C1: /tmp 单副本 → 仓库归档 (逐字) + manifest (sha256 读数)。

预注册 (eval/capability/exp1-q32/prereg_q32.json)
  · r3 (D-ARCH): 历史证据归档件**禁止改字节**; 自足化只在**入口层**做逐位还原 + 冲突 fail-closed。
  · r4: 新增归档文件必须与 /tmp 原件逐位相同 (sha256 相等有读数), sha 登记进本轮产物。

纪律:
  · 逐字复制 (shutil.copy2) + 读回复核 sha256 相等, 不等即 rc=2 并删除本次产物;
  · 幂等: 重跑时目标已存在且 sha 相同 ⇒ no-op (不动 mtime); sha 不同 ⇒ **拒绝覆盖** rc=2;
  · 源缺失 ⇒ rc=3 弃权 (该条目单列, 不当红不当绿);
  · 附带 ripple: 扫描每个归档件文本里的 /tmp 引用, 记入 manifest.deps (仅登记, 不修)。
退出码: 0 全过 / 2 断言失败 / 3 环境失败 (源缺失 ⇒ 该条目弃权)。
"""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
ARDIR = 'eval/capability/exp1-q32/archived_tmp'
MANIFEST = ARDIR + '/manifest.json'
TMP_RE = re.compile(r'/tmp[A-Za-z0-9._/\-]*')

# (name, 源 /tmp 路径, 归档相对路径, kind)
ENTRIES = [
    ('r462_e2e', '/tmp/r462_e2e.sh', ARDIR + '/r462/r462_e2e.sh', 'copy'),
    ('r462_negctl', '/tmp/r462_negctl.json', ARDIR + '/r462/r462_negctl.json', 'copy'),
    ('r457_run_agent_tools', '/tmp/r457_run_agent_tools.sh', ARDIR + '/r457/r457_run_agent_tools.sh', 'copy'),
    ('r457_nokey', '/tmp/r457_nokey.sh', ARDIR + '/r457/r457_nokey.sh', 'copy'),
    ('run_r374', '/tmp/gameprobe/run_r374.sh', ARDIR + '/gameprobe/run_r374.sh', 'copy'),
    ('r377_kpi_telemetry', '/tmp/gameprobe/r377_kpi.telemetry', ARDIR + '/gameprobe/r377_kpi.telemetry', 'copy'),
    ('fp375_probe', '/tmp/fp375/probe.py', ARDIR + '/fp375/probe.py', 'copy'),
    ('fp376_probe2', '/tmp/fp376/probe2.py', ARDIR + '/fp376/probe2.py', 'copy'),
    ('r382_plan_frontend_probe', '/tmp/r382/plan_frontend_probe.py', ARDIR + '/r382/plan_frontend_probe.py', 'copy'),
    ('r391probe_Program', '/tmp/r391probe/Program.cs', ARDIR + '/r391probe/Program.cs', 'copy', 'r391probe'),
    ('r391probe_csproj', '/tmp/r391probe/r391probe.csproj', ARDIR + '/r391probe/r391probe.csproj', 'copy', 'r391probe'),
    ('r462_corpus_repo_resident', '/tmp/r462_corpus.json', 'eval/rover/r462/corpus-r462-w.json', 'repo-resident', None),
]


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def deps_of(path):
    try:
        blob = open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return []
    return sorted(set(TMP_RE.findall(blob)))


def main():
    dry = '--dry-run' in sys.argv
    rows, rc = [], 0
    for name, src, rel, kind, *rest in ENTRIES:
        group = rest[0] if rest else None
        dst = os.path.join(ROOT, rel)
        row = {'name': name, 'kind': kind, 'origin': src, 'archive': rel, 'group': group}
        if kind == 'repo-resident':
            if not os.path.isfile(dst):
                row['verdict'] = 'archive_missing'
                rc = 2
            elif not os.path.isfile(src):
                row['verdict'] = 'origin_absent'
                rc = 3
            else:
                a, b = sha256(src), sha256(dst)
                row.update({'sha256': b, 'bytes': os.path.getsize(dst),
                            'same_as_origin': a == b, 'verdict': 'identical' if a == b else 'divergent'})
                if a != b:
                    rc = 2
        else:
            if not os.path.isfile(src):
                row['verdict'] = 'origin_absent'
                rc = 3
                print('  %-26s ORIGIN_ABSENT (%s) ⇒ 弃权' % (name, src))
                rows.append(row)
                continue
            ssha, sbytes = sha256(src), os.path.getsize(src)
            smode = stat.S_IMODE(os.stat(src).st_mode)
            row.update({'sha256': ssha, 'bytes': sbytes, 'mode': oct(smode)})
            if os.path.exists(dst):
                dsha = sha256(dst)
                if dsha != ssha:
                    row['verdict'] = 'REFUSE_divergent'
                    print('  %-26s REFUSE_divergent (归档件与原件不同, 禁覆盖)' % name)
                    rc = 2
                    rows.append(row)
                    continue
                row['verdict'] = 'noop_identical'
            else:
                if dry:
                    row['verdict'] = 'would_copy'
                else:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    dsha = sha256(dst)
                    if dsha != ssha or os.path.getsize(dst) != sbytes:
                        row['verdict'] = 'COPY_MISMATCH'
                        os.remove(dst)
                        rc = 2
                    else:
                        row['verdict'] = 'copied_verified'
            row['deps_tmp_refs'] = deps_of(dst)
        rows.append(row)
        print('  %-26s %-16s %s' % (name, row.get('verdict'), (row.get('sha256') or '')[:16]))

    n_copy = sum(1 for r in rows if r.get('verdict') in ('copied_verified', 'noop_identical'))
    n_ident = sum(1 for r in rows if r.get('verdict') == 'identical' or r.get('same_as_origin'))
    payload = {'round': 'EXP1-Q32', 'schema': 'tmp-archive-manifest/1', 'archived_dir': ARDIR,
               'n_entries': len(rows), 'n_archived_ok': n_copy, 'n_repo_resident_identical': n_ident,
               'rule': 'r3/r4: 逐字归档 + sha256 读数; 归档件禁改字节; 入口层 materialize 自足化',
               'entries': rows}
    if not dry:
        os.makedirs(os.path.join(ROOT, ARDIR), exist_ok=True)
        out = json.dumps(payload, ensure_ascii=False, indent=1) + '\n'
        with open(os.path.join(ROOT, MANIFEST), 'w', encoding='utf-8') as f:
            f.write(out)
        back = open(os.path.join(ROOT, MANIFEST), encoding='utf-8').read()
        print('WRITE_READBACK=%s' % ('OK' if back == out else 'MISMATCH'))
        if back != out:
            return 2
        print('落盘 %s (%d 条)' % (MANIFEST, len(rows)))
    print('ARCHIVE=%s entries=%d archived_ok=%d repo_resident_identical=%d'
          % ('FAIL' if rc == 2 else ('ABSTAIN' if rc == 3 else 'OK'), len(rows), n_copy, n_ident))
    return rc


if __name__ == '__main__':
    sys.exit(main())
