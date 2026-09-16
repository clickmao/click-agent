#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C1(自伤修复): 普查器的**输出面**必须与轮次绑定 (第二次同族自伤)。

事故: `instrument_gap_census_q30.py` 把 OUT 硬编码为 Q30 的冻结证据路径 ⇒ Q31 直接跑它会把
      Q30 的读数 (110 覆盖 / 105 有器具 / 5 缺口) **整份改写成 Q31 的读数**, 历史结论不可复现。
      (同族前例: Q17「器具默认 --out 指向轮次证据」、Q28 白名单器具默认 --out 指向冻结证据。)
修法: ①从 HEAD 还原 Q30 的冻结证据; ②**源码派生** Q31 版普查器 (只替换输出路径与轮号两处,
      其余逐行相同 —— 禁重写实现, 防两版逻辑漂移); ③跑 Q31 版并记录两版读数。
机检: 派生件与母体的逐行 diff 只允许出现在被替换的两行。
"""
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
SRC = 'eval/capability/exp1-q30/instrument_gap_census_q30.py'
DST = 'eval/capability/exp1-q31/instrument_gap_census_q31.py'
FROZEN = 'eval/capability/exp1-q30/instrument_gap_census_q30.json'
REPL = [("OUT = os.path.join(ROOT, 'eval/capability/exp1-q30/instrument_gap_census_q30.json')",
         "OUT = os.path.join(ROOT, 'eval/capability/exp1-q31/instrument_gap_census_q31.json')"),
        ("'round': 'EXP1-Q30'", "'round': 'EXP1-Q31'")]


def main():
    # ① 还原 Q30 冻结证据 (若已被本轮的误跑改写)
    st = subprocess.run(['git', 'status', '--porcelain', '--', FROZEN], cwd=ROOT,
                        capture_output=True, text=True).stdout.strip()
    if st:
        subprocess.run(['git', 'checkout', '--', FROZEN], cwd=ROOT, check=True)
        print('Q30_FROZEN_RESTORED (曾为: %s)' % st)
    else:
        print('Q30_FROZEN_CLEAN (无需还原)')
    head = subprocess.run(['git', 'show', 'HEAD:%s' % FROZEN], cwd=ROOT, capture_output=True,
                          check=True).stdout.decode('utf-8')
    q30 = json.loads(head)
    print('Q30_READING derived=%d no_instrument=%d by_class=%s rows_covered=%d'
          % (q30['derived_instrument'], q30['no_instrument'], q30['by_reason_class'], q30['rows_covered']))

    # ② 源码派生 Q31 版 (只允许两处替换)
    src = open(os.path.join(ROOT, SRC), encoding='utf-8').read()
    txt = src
    for a, b in REPL:
        assert txt.count(a) == 1, '母体缺少唯一锚点: %s' % a
        txt = txt.replace(a, b)
    open(os.path.join(ROOT, DST), 'w', encoding='utf-8').write(txt)
    diff = subprocess.run(['git', 'diff', '--no-index', '--unified=0',
                           os.path.join(ROOT, SRC), os.path.join(ROOT, DST)],
                          capture_output=True, text=True).stdout
    changed = [l for l in diff.splitlines() if l.startswith(('+', '-')) and not l.startswith(('+++', '---'))]
    print('DERIVED_LINES=%d (期望 4 = 2 行 × 删/增)' % len(changed))
    for l in changed:
        print('  %s' % l[:150])
    if len(changed) != 4:
        print('DERIVE=FAIL (派生件与母体差异超过被替换的两行 ⇒ 逻辑漂移)')
        return 2

    # ③ 跑 Q31 版
    p = subprocess.run(['python3', DST], cwd=ROOT, capture_output=True, text=True)
    print(p.stdout.strip())
    if p.returncode != 0:
        print('RUN=FAIL rc=%d\n%s' % (p.returncode, p.stderr[-400:]))
        return 2
    q31 = json.load(open(os.path.join(ROOT, 'eval/capability/exp1-q31/instrument_gap_census_q31.json'),
                        encoding='utf-8'))
    print('Q31_READING derived=%d no_instrument=%d by_class=%s rows_covered=%d'
          % (q31['derived_instrument'], q31['no_instrument'], q31['by_reason_class'], q31['rows_covered']))
    print('DELTA derived %+d / no_instrument %+d / rows_covered %+d'
          % (q31['derived_instrument'] - q30['derived_instrument'],
             q31['no_instrument'] - q30['no_instrument'], q31['rows_covered'] - q30['rows_covered']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
