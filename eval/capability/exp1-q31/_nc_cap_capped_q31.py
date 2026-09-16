#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C4 负控: 归因闸阈值器具的判别力自证 —— 喂一份 `capped=True` 的面记录。

`capped=True` 的语义 = 阈值对当前面规模过小 ⇒ 整面**弃权** (读数消失而非报错)。器具必须判红 (rc=2)。
若仍判绿, 说明余量判据空心 (未读 capped / 未真算余量)。
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip()
INSTR = 'eval/capability/exp1-q31/instruments/face_cap_headroom.py'


def main():
    tmp = tempfile.mkdtemp(prefix='q31-cap-nc-')
    rec = {'total': 24, 'side_effect_attribution': {
        'trace': {'commands': 52, 'log_bytes': 90_000_000, 'capped': True}}}
    p = os.path.join(tmp, 'face_capped.json')
    open(p, 'w', encoding='utf-8').write(json.dumps(rec))
    r = subprocess.run(['python3', INSTR, '--check', '--record', p], cwd=ROOT,
                       capture_output=True, text=True)
    out = (r.stdout or '') + (r.stderr or '')
    print(out.strip())
    if r.returncode == 2 and 'CAP_HEADROOM=FAIL' in out:
        print('NC_DETECTED (capped=True ⇒ 判红 rc=2)')
        return 0
    print('NC_NOT_DETECTED rc=%d' % r.returncode)
    return 1


if __name__ == '__main__':
    sys.exit(main())
