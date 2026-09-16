#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 自引用登记行的定向重审 (块级写路径; 承 EXP1-Q29 `apply_repin_q29.py` 纪律)。

用于两个**被 pin 的文件尚未提交**的行 (r444 证据=全量面记录, r476 证据=器具本体):
器具的 `--only` 派生读的是 `git status` ⇒ 未提交时该行只可能派生成 live/worktree-only,
故此处走块级替换 + **按文件字节**算 pin (口径: 「提交后该字节即冻结态」, 与 Q29 同源并显式打印)。

用法: python3 eval/capability/exp1-q30/apply_repin_rows_q30.py [--dry-run]
判据: 行数不变 ∧ 只有目标行变 ∧ 变更键集 ∈ {artifact_sha12, instrument_sha12, audited_by_round}
      ∧ 幂等 ∧ 写后读回 ∧ 尾形态保留。
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
REG = 'docs/verification-registry.json'
ROUND = 'EXP1-Q30'
TARGETS = ['r444.instrument-acceptance', 'r476.evidence-binding-round-param']
ALLOWED_KEYS = {'artifact_sha12', 'instrument_sha12', 'audited_by_round'}


def sha12(p):
    return hashlib.sha256(open(os.path.join(ROOT, p), 'rb').read()).hexdigest()[:12]


def block_insert(raw, row_id, new_field):
    i = raw.index('"id": "%s"' % row_id)
    j = raw.index('\n  },', i) + len('\n  },')
    block = raw[i:j]
    k = block.index('"evidence_generated_with": ')
    ls = block.rindex('\n', 0, k) + 1
    W = block[ls:k]
    ob = block.index('{', k)
    depth, p, in_str, esc = 0, ob, False, False
    while True:
        ch = block[p]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                break
        p += 1
    end = block.index('\n', p + 1)
    trailing = block[p + 1:end]
    old = json.loads(block[ob:p + 1])
    inner = json.dumps(new_field, indent=1, ensure_ascii=False).split('\n')
    lines = [W + '"evidence_generated_with": {'] + [W + l for l in inner[1:]]
    return raw[:i] + block[:ls] + '\n'.join(lines) + trailing + block[end:] + raw[j:], old, new_field


def main():
    dry = '--dry-run' in sys.argv
    reg_abs = os.path.join(ROOT, REG)
    raw = open(reg_abs, encoding='utf-8', newline='').read()
    doc = json.loads(raw)
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    tail = '\n' if raw.endswith('\n') else ''
    if ser + tail != raw:
        print('BLOCK_ASSERT=FAIL 全文件不可逐字节复现 (禁改写)')
        return 3
    print('BLOCK_ASSERT=OK (tail=%s)' % ('LF' if tail else 'NONE'))
    print('PIN_BASIS=file-bytes (未提交态; 提交后该字节即冻结态 —— 与 Q29 同口径)')

    rows = {r.get('id'): r for r in doc['rows']}
    out_raw, touched = raw, []
    for rid in TARGETS:
        r = rows.get(rid)
        if r is None:
            print('MEASURE/row_missing %s' % rid)
            return 3
        f = dict(r['evidence_generated_with'])
        new = dict(f)
        ep = r['evidence_path']
        if f.get('pin_status') == 'frozen' and f.get('evidence_kind') == 'artifact':
            new['artifact_sha12'] = sha12(ep)
        if f.get('instrument'):
            new['instrument_sha12'] = sha12(f['instrument'])
        new['audited_by_round'] = ROUND
        if new == f:
            print('IDEMPOTENT %-42s (无需重审)' % rid)
            continue
        ck = sorted(k for k in set(list(f) + list(new)) if f.get(k) != new.get(k))
        if not set(ck) <= ALLOWED_KEYS:
            print('MEASURE/keys_out_of_scope %s: %s' % (rid, ck))
            return 3
        out_raw, old, _ = block_insert(out_raw, rid, new)
        touched.append((rid, ck))
        print('REPIN %-42s %s' % (rid, dict((k, (f.get(k), new.get(k))) for k in ck)))

    if not touched:
        print('IDEMPOTENT=OK (两个目标行均无需重审)')
        return 0
    d_new = json.loads(out_raw)
    if len(d_new['rows']) != len(doc['rows']):
        print('BLOCK_ASSERT=FAIL 行数变化')
        return 3
    b2 = {r.get('id'): r for r in d_new['rows']}
    changed = sorted(i for i in b2 if b2[i] != rows.get(i))
    if changed != sorted(t[0] for t in touched):
        print('BLOCK_ASSERT=FAIL 变更行集不符: %s' % changed)
        return 3
    print('BLOCK_ASSERT=OK 变更行集=%s' % changed)
    if dry:
        print('DRY_RUN=OK (未写盘)')
        return 0
    open(reg_abs, 'w', encoding='utf-8', newline='').write(out_raw)
    back = open(reg_abs, encoding='utf-8', newline='').read()
    print('WRITE_READBACK=%s' % ('OK' if back == out_raw else 'MISMATCH'))
    d3 = json.loads(back)
    print('TAIL_FORM_PRESERVED=%s' % (json.dumps(d3, indent=1, ensure_ascii=False) + tail == back))
    print(subprocess.run(['git', 'diff', '--numstat', '--', REG], cwd=ROOT, capture_output=True,
                         text=True).stdout.strip())
    return 0 if back == out_raw else 2


if __name__ == '__main__':
    sys.exit(main())
