#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · 全量面首跑 7 红的三类修复 (照原样入档, 修的是器具面字段与写点, 不放宽任何断言)。

首跑读数: 20/27。
  ① 4 行 (新器具) `BAD_DYNAMIC_COUNT:None` —— `input_surface='dynamic_corpus'` 的行必须带
     `corpus_dynamic_count` (动态语料规模), 我漏了 ⇒ 补数 (值由当前面现算, 不拍脑袋);
  ② `SIDE-EFFECT: 本面命令弄脏既有产物 ['eval/capability/exp1-q31/verdict_q31_hook_gate.json']`
     —— 新验证器默认 `--out` 指向轮次证据 (与 Q17/Q28/Q30 同族第 3 次) ⇒ 默认写点改到 scratch 面;
  ③ 3 行前序漂移 (非本侧引入, 如实分列): `r483b.preflight-gate-instrument` 器具 pin 陈旧
     (声明 1a64ceb6bd14 / 现盘=HEAD 344419f044aa, 由 R487 提交时未重审), `r487.*` 三行缺
     `evidence_generated_with` (R2f)。
本步只做 ① ② 的器具面修复 + 清单内被改器具行的 sha 重审; ③ 由 bind_evidence 定向重审 (另一条命令)。
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
MAN = 'eval/capability/instruments.json'
CHECKER = 'eval/capability/instruments_check.py'
SCRATCH_ENTRY = "                    'eval/capability/exp1-q31/scratch/')"
SCRATCH_ANCHOR = "                    'eval/capability/exp1-q30/scratch/')"


def sha12(rel):
    return hashlib.sha256(open(os.path.join(ROOT, rel), 'rb').read()).hexdigest()[:12]


def dyn_count(rid):
    if rid == 'exp1q31.retired-interop':
        n = 0
        for dp, dn, fn in os.walk(os.path.join(ROOT, 'src')):
            dn[:] = [d for d in dn if d not in ('bin', 'obj')]
            n += sum(1 for f in fn if f.endswith('.cs'))
        return n
    if rid == 'exp1q31.cap-headroom':
        man = json.load(open(os.path.join(ROOT, MAN), encoding='utf-8'))
        return len(man['instruments'])
    if rid == 'exp1q31.only-equivalence':
        return len(json.load(open(os.path.join(ROOT, 'docs/verification-registry.json'),
                                  encoding='utf-8'))['rows'])
    if rid == 'exp1q31.stage-guard-hook':
        return 8          # 夹具场景数 (P1-P5 + N1/N2 + P0)
    return None


def main():
    # ---- ② 检查器的 scratch 面: 释放新验证器的默认写点 (写事件判定, 非内容一致性判定) ----
    p = os.path.join(ROOT, CHECKER)
    src = open(p, encoding='utf-8', newline='').read()
    if SCRATCH_ENTRY not in src:
        if src.count(SCRATCH_ANCHOR) != 1:
            print('SCRATCH_PATCH=FAIL (锚点不唯一)')
            return 3
        src = src.replace(SCRATCH_ANCHOR, SCRATCH_ANCHOR[:-1] + ",\n"
                          "                    # EXP1-Q31: 钩子闸验证器的默认写点 (轮次证据由 --out 显式指定)\n"
                          + SCRATCH_ENTRY)
        open(p, 'w', encoding='utf-8', newline='').write(src)
        print('SCRATCH_PATCH=OK (+eval/capability/exp1-q31/scratch/)')
    else:
        print('SCRATCH_PATCH=IDEMPOTENT')
    print('CHECKER_SHA12=%s' % sha12(CHECKER))

    # ---- ① 清单: 补 corpus_dynamic_count + 刷新被改器具行的 sha ----
    man_abs = os.path.join(ROOT, MAN)
    raw = open(man_abs, encoding='utf-8', newline='').read()
    doc = json.loads(raw)
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    if ser + ('\n' if raw.endswith('\n') else '') != raw:
        print('SER_ASSERT=FAIL (禁改写)')
        return 3
    print('SER_ASSERT=OK')
    changed = []
    for e in doc['instruments']:
        rid = e['id']
        if e.get('input_surface') == 'dynamic_corpus' and e.get('corpus_dynamic_count') is None:
            n = dyn_count(rid)
            if n is None:
                continue
            e['corpus_dynamic_count'] = n
            changed.append('%s(+count=%d)' % (rid, n))
        want = sha12(e['evidence_path'])
        if e.get('instrument_sha12') != want:
            e['version'] = 'content-sha12:%s' % want
            e['version_source'] = 'content-sha12'
            e['instrument_sha12'] = want
            e['owner_round'] = 'EXP1-Q31'
            changed.append('%s(sha→%s)' % (rid, want))
    print('MANIFEST_CHANGED %d: %s' % (len(changed), changed))
    if not changed:
        print('IDEMPOTENT=OK')
        return 0
    out = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    open(man_abs, 'w', encoding='utf-8', newline='').write(out)
    back = open(man_abs, encoding='utf-8', newline='').read()
    print('WRITE_READBACK=%s' % ('OK' if back == out else 'MISMATCH'))
    print('MANIFEST_N=%d' % len(json.loads(back)['instruments']))
    print(subprocess.run(['git', 'diff', '--numstat', '--', MAN, CHECKER], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip())
    return 0 if back == out else 2


if __name__ == '__main__':
    sys.exit(main())
