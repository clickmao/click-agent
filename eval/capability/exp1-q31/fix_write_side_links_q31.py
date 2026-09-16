#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C6 (R486 §5 残留 8): `docs/improvements.md` 5 条**根相对误写**的修复 + 写侧探针复跑。

R486 机检: 87 条路径引用中「误写 5」(写成根相对 `docs/…` 而引用方在 docs/ 内 ⇒ 解析成 `docs/docs/…`)。
裁定: 写侧可修 (改成 `./…`), 判据属写侧不属解析器。本步:
  ① 只改 **markdown 链接目标** `](docs/…)` → `](./…)`; 反引号**提及** (`` `docs/…` ``) 一律不动
     (它们在正文里作为路径文本是正确的, 且 R486 判据只覆盖链接目标);
  ② 机检: 每条链接改前/改后计数 = 1; 提及计数前后不变 (守恒式);
  ③ 复跑写侧探针 (--out → Q31 命名空间, 不覆盖 R486 记录): 期望 moved 5 → 0, resolved 79 → 84, 守恒成立。
"""
import json
import os
import re
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
DOC = 'docs/improvements.md'
PATHS = ['docs/plans/v0.22.0-exp8-artifact-to-skill-and-kpi-ab.md',
         'docs/验证形式规范.md',
         'docs/verification-registry.json',
         'docs/plans/v0.22.0-l2-capability-diff.md',
         'docs/plans/v0.22.0-exploration-index.md']
PROBE = 'eval/recall/r486/write_side_address_probe.py'
PROBE_BEFORE = 'eval/recall/r486/write-side.json'
PROBE_AFTER = 'eval/capability/exp1-q31/write_side_after_q31.json'


def count_link(t, p):
    return len(re.findall(r'\]\(' + re.escape(p) + r'\)', t))


def count_fixed(t, p):
    return len(re.findall(r'\]\(\./' + re.escape(p[len('docs/'):]) + r'\)', t))


def count_mention(t, p):
    return len(re.findall(r'`' + re.escape(p) + r'`', t))


def main():
    p_abs = os.path.join(ROOT, DOC)
    t = open(p_abs, encoding='utf-8', newline='').read()
    m0 = {p: count_mention(t, p) for p in PATHS}
    l0 = {p: count_link(t, p) for p in PATHS}
    f0 = {p: count_fixed(t, p) for p in PATHS}
    print('BEFORE link=%s fixed=%s mention=%s' % (sum(l0.values()), sum(f0.values()), sum(m0.values())))
    new = t
    changed = []
    for p in PATHS:
        old = '](' + p + ')'
        newtok = '](./' + p[len('docs/'):] + ')'
        n = new.count(old)
        if n == 0:
            continue
        if new.count(newtok) > 0:
            print('SKIP %s (已是 ./ 形态)' % p)
            continue
        if n != 1:
            print('ABORT %s: 链接形态计数 %d ≠ 1 (不批量改未知语境)' % (p, n))
            return 2
        new = new.replace(old, newtok)
        changed.append(p)
    print('LINKS_FIXED %d: %s' % (len(changed), [c.split('/')[-1] for c in changed]))
    m1 = {p: count_mention(new, p) for p in PATHS}
    if m1 != m0:
        print('MENTION_CONSERVATION=FAIL 前=%s 后=%s' % (m0, m1))
        return 2
    print('MENTION_CONSERVATION=OK (反引号提及 %d 处未动)' % sum(m1.values()))
    if not changed:
        print('IDEMPOTENT=OK')
    else:
        open(p_abs, 'w', encoding='utf-8', newline='').write(new)
        back = open(p_abs, encoding='utf-8', newline='').read()
        print('WRITE_READBACK=%s (bytes %d -> %d)' % ('OK' if back == new else 'MISMATCH', len(t), len(new)))
        if back != new:
            return 2
    # 复跑探针 (before 记录先归档到 Q31 命名空间)
    if not os.path.isfile(os.path.join(ROOT, PROBE_AFTER.split('after')[0] + 'before_q31.json')):
        before_copy = 'eval/capability/exp1-q31/write_side_before_q31.json'
        if os.path.isfile(os.path.join(ROOT, PROBE_BEFORE)):
            open(os.path.join(ROOT, before_copy), 'w', encoding='utf-8').write(
                open(os.path.join(ROOT, PROBE_BEFORE), encoding='utf-8', newline='').read())
            print('BEFORE_ARCHIVED %s' % before_copy)
    r = subprocess.run(['python3', PROBE, '--out', PROBE_AFTER], cwd=ROOT, capture_output=True, text=True)
    print((r.stdout or '').strip()[-900:])
    if r.returncode != 0:
        print('PROBE_RC=%d' % r.returncode)
        return 2
    after = json.load(open(os.path.join(ROOT, PROBE_AFTER), encoding='utf-8-sig'))
    before = json.load(open(os.path.join(ROOT, PROBE_BEFORE), encoding='utf-8-sig'))
    print('AFTER classes=%s' % json.dumps(after['classes'], ensure_ascii=False))
    print('BEFORE classes=%s' % json.dumps(before['classes'], ensure_ascii=False))
    ok = (after['classes'].get('moved', 0) == 0 and after['conservation']['ok']
          and after['classes'].get('resolved', 0) >= before['classes'].get('resolved', 0))
    print('C6_VERDICT=%s (moved 5→%s, resolved %s→%s)'
          % ('PASS' if ok else 'FAIL', after['classes'].get('moved'), before['classes'].get('resolved'),
             after['classes'].get('resolved')))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
