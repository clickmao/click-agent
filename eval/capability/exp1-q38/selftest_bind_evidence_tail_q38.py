#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q38 · 候选③ 的**影子自检**: 尾契约字段 `noncanonical_input` 的双向回放 (成对判据)。

命题: 契约违反 (登记表 JSON 尾缺 LF) 必须成为**一等可见字段**, 而不是 stdout 里的一句人话。
判据必须成对, 只测一侧等于没测:
  c1 规范输入 (尾 = LF)  ⇒ flag == 0 ∧ reason is None          ← 防「标签恒真」(把正常输入也标成非规范)
  c2 非规范输入 (尾被摘掉) ⇒ flag == 1 ∧ reason == tail_lf_missing ← 防「标签恒假」(违反静默消失)
  c3 非规范输入写盘后尾被规范化 (LF) 且**语义零变化** (json 内容逐字段相等)
  c4 记录键齐备 (字段存在性): noncanonical_input / noncanonical_reason / tail_contract /
     registry_tail_input / ser_assert / rc 全在
  c5 双跑标签**互异** (标签不是常量)
  c6 真登记表零触碰: 两次跑都出现 `NUMSTAT=skip (scratch 副本)` 且真实登记表字节不变
  c7 幂等: 规范输入复跑 ⇒ IDEMPOTENT=OK

全部在 /tmp 的 scratch 副本上跑 (绝对路径 ⇒ 工具自报 scratch), 真登记表只被**读** (字节比对)。"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REG = ROOT / 'docs/verification-registry.json'
SCRATCH = pathlib.Path('/tmp/q38_bind_scratch')
OUT = HERE / 'bind_evidence_tail_selftest_q38.json'
ROW = 'r476.evidence-binding-round-param'
KEYS = ('noncanonical_input', 'noncanonical_reason', 'tail_contract', 'registry_tail_input',
        'ser_assert', 'rc')


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def run(reg, tag):
    rec = SCRATCH / ('record_%s.json' % tag)
    cmd = [sys.executable, 'eval/capability/bind_evidence.py', '--registry', str(reg),
           '--apply', '--only', ROW, '--round', 'EXP1-Q38', '--run-record', str(rec)]
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    out = (p.stdout or '') + (p.stderr or '')
    body = pathlib.Path(reg).read_bytes()
    return {'rc': p.returncode, 'stdout_tail': out.strip().splitlines()[-6:], 'stdout': out,
            'record': json.loads(rec.read_text(encoding='utf-8')) if rec.exists() else None,
            'file_tail_lf': body.endswith(b'\n'),
            'file_sha12': hashlib.sha256(body).hexdigest()[:12]}


def main():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)
    real_before = sha(REG)
    raw = REG.read_bytes()
    assert raw.endswith(b'\n'), '前提: 真登记表当前应为规范形 (LF)'
    can = SCRATCH / 'canonical.json'
    non = SCRATCH / 'noncanonical.json'
    can.write_bytes(raw)
    non.write_bytes(raw[:-1])                      # 摘掉尾 LF = 契约违形态

    a = run(can, 'canonical')
    b = run(non, 'noncanonical')
    c = run(can, 'canonical_rerun')

    ra, rb, rc_ = a['record'], b['record'], c['record']
    checks = {
        'c1_canonical_flag_false': bool(ra and ra['noncanonical_input'] is False
                                        and ra['noncanonical_reason'] is None
                                        and ra['registry_tail_input'] == 'LF'
                                        and 'NONCANONICAL_INPUT=0' in a['stdout'] and a['rc'] == 0),
        'c2_noncanonical_flag_true': bool(rb and rb['noncanonical_input'] is True
                                          and rb['noncanonical_reason'] == 'tail_lf_missing'
                                          and rb['registry_tail_input'] == 'NONE'
                                          and 'NONCANONICAL_INPUT=1' in b['stdout'] and b['rc'] == 0),
        'c3_tail_normalized_and_semantics_unchanged': bool(
            b['file_tail_lf']
            and json.loads(non.read_text(encoding='utf-8')) == json.loads(can.read_text(encoding='utf-8'))),
        'c4_record_keys_present': bool(ra and rb and all(k in ra for k in KEYS) and all(k in rb for k in KEYS)),
        'c5_flag_not_constant': bool(ra and rb and ra['noncanonical_input'] != rb['noncanonical_input']),
        'c6_real_registry_untouched': bool('NUMSTAT=skip' in a['stdout'] and 'NUMSTAT=skip' in b['stdout']
                                           and sha(REG) == real_before),
        'c7_idempotent_on_canonical_rerun': bool(rc_ and rc_['idempotent'] is True
                                                 and 'IDEMPOTENT=OK' in c['stdout']),
    }
    ok = all(checks.values())
    payload = {
        'round': 'EXP1-Q38', 'schema': 'bind-evidence-tail-selftest/1',
        'subject': 'eval/capability/bind_evidence.py --run-record / noncanonical_input',
        'scratch_root': str(SCRATCH), 'real_registry_sha12_before': real_before[:12],
        'real_registry_sha12_after': sha(REG)[:12],
        'cases': {'canonical': {k: v for k, v in a.items() if k != 'stdout'},
                  'noncanonical': {k: v for k, v in b.items() if k != 'stdout'},
                  'canonical_rerun': {k: v for k, v in c.items() if k != 'stdout'}},
        'checks': checks, 'verdict': 'PASS' if ok else 'FAIL',
        'note': ('双跑成对: 规范形 ⇒ flag=0 / 非规范形 ⇒ flag=1 且尾被规范化 (语义零变化)。'
                 'c6 证明真登记表只被读 (scratch 绝对路径 ⇒ NUMSTAT=skip)。'),
    }
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    print('SELFTEST %s' % json.dumps(checks, ensure_ascii=False))
    print('flags: canonical=%s noncanonical=%s rerun_idempotent=%s'
          % (ra and ra['noncanonical_input'], rb and rb['noncanonical_input'],
             rc_ and rc_['idempotent']))
    print('VERDICT=%s out=%s' % (payload['verdict'], OUT.name))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
