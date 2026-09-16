#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C1裁定④: r462 权重探针的**自足入口** (归档已在前序轮完成, 声明命令却仍指 /tmp)。

现盘机检发现 (存在面 ≠ 扫描面):
  · eval/rover/r462/ 内已有 **逐位相同** 的归档副本 (bench_r462_w.py / corpus-r462-w.json /
    report_r462_w.py 三对 sha256 与 /tmp 原件完全一致) ⇒ 「器具不在仓库内」的前提**为假**;
  · 缺口在**声明层**: registry 行的 evidence_cmd 仍写 `python3 /tmp/r462_w_bench.py …`;
  · 且归档**不自足**: bench_r462_w.py 内 `CORPUS = "/tmp/r462_corpus.json"` 硬编码 /tmp 输入。
本器 = 归档的可机检入口:
  --check    : 三对归档逐位同一 (sha256) + 记录硬编码输入事实; 真跑未做 ⇒ 显式 EXECUTION_BLOCKED
  --run      : 真跑配方 (需 --gguf 模型 + llama-server; 本轮未执行)
  --selftest : 同一性判据的夹具 (相同/不同/缺失)
纪律: 禁止改写归档件本身 (它是历史证据), 自足入口只做**校验 + 显式受阻标记**。
退出码: 0 通过 / 2 断言失败 / 3 环境失败 (原件已不在 ⇒ 同一性不可判, 弃权)。
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
PAIRS = [('eval/rover/r462/bench_r462_w.py', '/tmp/r462_w_bench.py'),
         ('eval/rover/r462/corpus-r462-w.json', '/tmp/r462_corpus.json'),
         ('eval/rover/r462/report_r462_w.py', '/tmp/r462_w_report.py')]
HARDCODED = [('eval/rover/r462/bench_r462_w.py', 'CORPUS = "/tmp/r462_corpus.json"')]
OUT_ID = 'eval/capability/exp1-q31/tmp_archive_identity_q31.json'


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def identity(pairs, base=ROOT):
    """返回 (rows, rc): 逐对 sha256 比较。原件缺失 ⇒ rc=3 (弃权, 不判红不判绿)。"""
    rows, abstain, bad = [], False, False
    for repo_rel, orig in pairs:
        rp = os.path.join(base, repo_rel)
        row = {'repo': repo_rel, 'origin': orig}
        if not os.path.isfile(rp):
            row['verdict'] = 'repo_missing'
            bad = True
        elif not os.path.isfile(orig):
            row['verdict'] = 'origin_absent'
            abstain = True
        else:
            a, b = sha256(rp), sha256(orig)
            row.update({'sha256': a, 'same': a == b, 'bytes': os.path.getsize(rp)})
            row['verdict'] = 'identical' if a == b else 'divergent'
            bad = bad or (a != b)
        rows.append(row)
    rc = 3 if abstain else (2 if bad else 0)
    return rows, rc


FIX = [
    ('identical', b'abc', b'abc', 0),
    ('divergent', b'abc', b'abd', 2),
    ('repo_missing', None, b'abc', 2),
    ('origin_absent', b'abc', None, 3),
]


def selftest():
    bad = 0
    tmp = tempfile.mkdtemp(prefix='q31-ident-')
    try:
        for name, rbody, obody, want in FIX:
            rp = os.path.join(tmp, 'repo_%s' % name)
            op = os.path.join(tmp, 'orig_%s' % name)
            if rbody is not None:
                open(rp, 'wb').write(rbody)
            if obody is not None:
                open(op, 'wb').write(obody)
            rows, rc = identity([('repo_%s' % name, op)], base=tmp)
            ok = (rc == want)
            if not ok:
                bad += 1
            print('%-16s expect_rc=%d got=%d (%s) %s' % (name, want, rc, rows[0]['verdict'], 'OK' if ok else 'FAIL'))
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    print('SELFTEST %s (%d/%d)' % ('PASS' if bad == 0 else 'FAIL', len(FIX) - bad, len(FIX)))
    return 0 if bad == 0 else 2


def main():
    if '--selftest' in sys.argv:
        return selftest()
    if '--run' in sys.argv:
        gguf = sys.argv[sys.argv.index('--gguf') + 1] if '--gguf' in sys.argv else None
        if not gguf or not os.path.isfile(gguf):
            print('ENV_FAIL: --run 需要 --gguf <存在的模型文件>')
            return 3
        tag = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else 'q31'
        cmd = ['python3', os.path.join(ROOT, 'eval/rover/r462/bench_r462_w.py'), '--model', gguf,
               '--tag', tag, '--port', '48790', '--ctx', '1024', '--out',
               os.path.join(ROOT, 'eval/rover/r462/w-%s.json' % tag)]
        print('R462_RUN_CMD %s' % ' '.join(cmd))
        return subprocess.run(cmd, cwd=ROOT, check=False).returncode
    rows, rc = identity(PAIRS)
    n_same = sum(1 for r in rows if r.get('same'))
    print('R462_ARCHIVE_IDENTITY %d/%d 逐位相同' % (n_same, len(rows)))
    for r in rows:
        print('  %-44s %-14s %s' % (r['repo'], r['verdict'], (r.get('sha256') or '')[:16]))
    hard = []
    for rel, lit in HARDCODED:
        blob = open(os.path.join(ROOT, rel), encoding='utf-8', errors='replace').read()
        hit = lit in blob
        hard.append({'file': rel, 'literal': lit, 'present': hit})
        print('  HARDCODED_INPUT %-40s %s' % (lit, 'present (归档不自足 ⇒ 需 wrapper)' if hit else 'absent'))
    payload = {'round': 'EXP1-Q31', 'schema': 'tmp-archive-identity/1', 'rows': rows,
               'n_identical': n_same, 'n_pairs': len(rows), 'hardcoded_inputs': hard,
               'execution_state': 'execution_blocked',
               'execution_blocker': 'needs gguf model + llama-server (--run); 本轮只做同一性校验与受阻标记',
               'rerun_recipe': 'python3 eval/capability/exp1-q31/instruments/r462_w_probe_wrapper.py --run --gguf <model.gguf> --tag <tag>'}
    out = os.path.join(ROOT, OUT_ID)
    open(out, 'w', encoding='utf-8').write(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
    print('EXECUTION_BLOCKED=needs_gguf+llama-server (真跑未执行, 不宣称已验证)')
    print('落盘 %s' % OUT_ID)
    if rc == 3:
        print('R462_ARCHIVE=ABSTAIN (/tmp 原件已不在 ⇒ 同一性不可判)')
    elif rc == 2:
        print('R462_ARCHIVE=FAIL (归档与原件不一致或归档缺失)')
    else:
        print('R462_ARCHIVE=OK (%d/%d 逐位相同)' % (n_same, len(rows)))
    return rc


if __name__ == '__main__':
    sys.exit(main())
