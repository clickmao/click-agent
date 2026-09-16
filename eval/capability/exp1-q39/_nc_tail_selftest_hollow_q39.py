#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q39 · 负控 (③ 尾契约影子自检): 判别力自证 —— 标签改成**常量**后自检必须判红。

形态: 复制 `bind_evidence.py` 到 /tmp, 做两处**语义保持**的变异, 让 `noncanonical_input` 恒假
(「标签恒真/恒假」这一类空心仪器的标准形态):
  m1 stdout 行 `% (1 if noncanonical else 0, ...)` → `% (0, ...)`   (占位符与实参一一对应, 不触发格式错)
  m2 运行记录 `"noncanonical_input": bool(noncanonical)` → `False`
再用环境覆盖 `AGENTFRAMEWORK_BIND_TOOL` 让 Q38 自检跑这个变异体, 输出改写指
`AGENTFRAMEWORK_TAIL_SELFTEST_OUT` ⇒ **真证据文件零触碰**。

期望: 自检的成对判据 (c2 非规范输入 ⇒ flag=1 / c5 双跑互异) 必须红 (rc=2 ∧ `VERDICT=FAIL`)。
     变异体下若自检仍绿 ⇒ 该自检判不出「标签恒定」, 本负控以 nc_exit=1 报 `NC_NOT_DETECTED`。
     锚点计数 ≠1 ⇒ rc=2 弃权 (器具已改版 ⇒ 负控需重写, 不静默通过)。

退出码: 0 = 负控成立 / 1 = 未检出 (自检空心, 面必红) / 2 = 弃权 (锚点失效)。
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SUBJECT = ROOT / 'eval/capability/bind_evidence.py'
SELFTEST = ROOT / 'eval/capability/exp1-q38/selftest_bind_evidence_tail_q38.py'
M1 = '% (1 if noncanonical else 0, NONCANON_REASON if noncanonical else "none", reg_rel, TAIL_CONTRACT))'
M1_NEW = '% (0, NONCANON_REASON if noncanonical else "none", reg_rel, TAIL_CONTRACT))'
M2 = '"noncanonical_input": bool(noncanonical),'
M2_NEW = '"noncanonical_input": False,'


def main():
    src = SUBJECT.read_text(encoding='utf-8')
    for pat in (M1, M2):
        n = src.count(pat)
        if n != 1:
            print('MUTATION_ANCHOR n=%d for %r ⇒ 弃权 (器具已改版, 负控需重写)' % (n, pat[:40]))
            return 2
    tmp = tempfile.mkdtemp(prefix='q39-nc-tail-')
    try:
        mutated = src.replace(M1, M1_NEW).replace(M2, M2_NEW)
        mut = pathlib.Path(tmp) / 'bind_evidence_const_flag.py'
        mut.write_text(mutated, encoding='utf-8')
        # 变异体自检: 两处锚点确实已被替换 (否则负控在测别的东西)
        body = mut.read_text(encoding='utf-8')
        assert M1_NEW in body and M2_NEW in body and M1 not in body and M2 not in body
        out = pathlib.Path(tmp) / 'selftest_mutated.json'
        env = dict(os.environ)
        env['AGENTFRAMEWORK_BIND_TOOL'] = str(mut)
        env['AGENTFRAMEWORK_TAIL_SELFTEST_OUT'] = str(out)
        p = subprocess.run([sys.executable, str(SELFTEST)], cwd=str(ROOT), capture_output=True,
                           text=True, env=env)
        txt = (p.stdout or '') + (p.stderr or '')
        print('MUTATED_SELFTEST rc=%d' % p.returncode)
        print('\n'.join(txt.strip().splitlines()[-3:]))
        if p.returncode == 2 and 'VERDICT=FAIL' in txt:
            print('NC_DETECTED (标签恒假的变异体 ⇒ 自检判红: c2/c5 成对判据有判别力)')
            return 0
        print('NC_NOT_DETECTED rc=%d (自检在变异体上仍绿 ⇒ 空心)' % p.returncode)
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
