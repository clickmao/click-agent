#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C3 负控: 钩子闸验证器的**判别力自证** (把钩子里的 stage-guard 段拿掉 ⇒ 验证器必须判红)。

形态: 在临时树里重建「没有 stage-guard 段的钩子」, 令验证器以该树为 ROOT 运行 ⇒ 期望它判红 (rc=2,
P3_拒绝对侧在飞 = FAIL)。若仍绿, 说明验证器测的是别的东西 (或只测钩子存在性)。
"""
import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip()
VER = 'eval/capability/exp1-q31/verify_stage_guard_hook_q31.py'
GUARD = 'eval/capability/exp1-q30/stage_guard_q30.py'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    tmp = tempfile.mkdtemp(prefix='q31-hook-nc-')
    try:
        os.makedirs(os.path.join(tmp, 'tools/hooks'))
        os.makedirs(os.path.join(tmp, 'eval/capability/exp1-q30'))
        txt = open(os.path.join(ROOT, 'tools/hooks/pre-commit'), encoding='utf-8').read()
        i, j = txt.index('# EXP1-Q31:'), txt.rindex('exit 0')
        hollow = txt[:i] + txt[j:]
        assert 'AGENTFRAMEWORK_STAGE_MANIFEST' not in hollow
        open(os.path.join(tmp, 'tools/hooks/pre-commit'), 'w', encoding='utf-8').write(hollow)
        shutil.copy(os.path.join(ROOT, GUARD), os.path.join(tmp, 'eval/capability/exp1-q30/stage_guard_q30.py'))
        v = load(VER, 'v_q31')
        v.ROOT = tmp
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = v.main()
        out = buf.getvalue()
        print('\n'.join(out.strip().splitlines()[-4:]))
        if rc == 2 and 'P3_拒绝对侧在飞' in out and 'FAIL' in out:
            print('NC_DETECTED (空心钩子 ⇒ 验证器判红 rc=2)')
            return 0
        print('NC_NOT_DETECTED rc=%d' % rc)
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
