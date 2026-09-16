#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C5 负控: 等价闸的**判别力自证** (注入轮号参数不一致 ⇒ 必须判红)。

形态: 把持 Q30 等价判据的两条写路径, 人为让「文本外科手术」路径用**另一个轮号参数** ⇒ 产物必须不同 ⇒
      等价闸必须报 P1 红。若注入后仍绿, 说明闸空心 (比较变量写反/未真正比较字节)。
"""
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip()
GUARD = 'eval/capability/exp1-q31/instruments/only_equivalence_guard.py'


def main():
    p = subprocess.run(['python3', GUARD, '--inject-defect', 'round-param-mismatch'], cwd=ROOT,
                       capture_output=True, text=True)
    out = (p.stdout or '') + (p.stderr or '')
    print(out.strip())
    if p.returncode == 0 and 'NC_DETECTED' in out:
        print('INJECT_MODE_OK: 注入轮号不一致 ⇒ 等价判据判红 (判别力非空心)')
        return 0
    print('NC_NOT_DETECTED rc=%d' % p.returncode)
    return 1


if __name__ == '__main__':
    sys.exit(main())
