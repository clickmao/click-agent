#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q39 · 负控 (② 目录结点归档器): 判别力自证 —— 把**抽取器置空**后归档器必须判红。

形态: 以模块方式加载 `archive_dir_nodes_q38.py`, 把它的 `load_mod` 换成「返回**抽不出任何引用**的
q34 代理」的版本, 并把它的 `ARCH` / `OUT` / `LISTONLY` 全部改指 `/tmp` 夹具目录 (真证据零触碰)。

期望: 归档器的等价面判据 (c2「从归档副本重跑抽取 ⇒ n_refs 与现场逐结点相等」) **必须红** (rc=2)。
      若空抽取仍 PASS ⇒ 该判据是空心的 (自证), 本负控即以 nc_exit=1 报 `NC_NOT_DETECTED`。

退出码: 0 = 负控成立 (归档器判红且被本件读到) / 1 = 未检出 (真空心, 面必红)。
"""
import contextlib
import importlib.util
import io
import os
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SUBJECT = ROOT / 'eval/capability/exp1-q38/archive_dir_nodes_q38.py'


class HollowQ34:
    """只保留遍历/文本性判定, 把「抽取引用」置空 —— 模拟抽取器空转。"""

    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    def refs_in(self, path):
        return []


def main():
    if not SUBJECT.exists():
        print('SUBJECT_MISSING %s' % SUBJECT)
        return 1
    tmp = tempfile.mkdtemp(prefix='q39-nc-archive-')
    try:
        spec = importlib.util.spec_from_file_location('arch_q39_nc', str(SUBJECT))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        real_load = m.load_mod

        def hollow_load(name, path):
            mod = real_load(name, path)
            if hasattr(mod, 'q34mod'):
                real_q34 = mod.q34mod()
                mod.q34mod = lambda: HollowQ34(real_q34)
            return mod

        m.load_mod = hollow_load
        m.ARCH = pathlib.Path(tmp) / 'arch'
        m.OUT = pathlib.Path(tmp) / 'out.json'
        m.LISTONLY = pathlib.Path(tmp) / 'listonly'
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = m.main()
        txt = buf.getvalue()
        verdict = 'FAIL' if 'VERDICT=FAIL' in txt else ('PASS' if 'VERDICT=PASS' in txt else None)
        print('\n'.join(txt.strip().splitlines()[-3:]))
        print('HOLLOW_RUN rc=%d verdict=%s (真证据目录零触碰: %s)' % (rc, verdict, SUBJECT.name))
        if rc == 2 and verdict == 'FAIL':
            print('NC_DETECTED (抽取器置空 ⇒ 归档器判红: 等价面判据与真实抽取绑定, 非自证)')
            return 0
        print('NC_NOT_DETECTED rc=%d verdict=%s' % (rc, verdict))
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
