#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · Q28 白名单覆盖面核验器的负向控制 (注入 = 把归一函数换成恒等函数)。

期望: 恒等归一 ⇒ run_probe 阶段残留 47 处墙钟装饰未被吃掉, 且脚本自带的 anti_hollow 对照翻红
⇒ 报告 `ok` 必须为 false。检出 ⇒ 印 NC_DETECTED rc=0; 若恒等归一后仍报 ok=true ⇒ 器具空心, rc=1。
"""
import importlib.util
import json
import sys

WL = 'eval/capability/exp1-q28/verify_whitelist_q28.py'
OUT = 'eval/capability/exp1-q30/scratch/_nc_wl_identity.json'


def main():
    spec = importlib.util.spec_from_file_location('wl', WL)
    assert spec is not None and spec.loader is not None, 'MEASURE-FAIL: 无法加载 %s' % WL
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.norm = lambda s: s                      # 注入: 恒等归一 (白名单失效)
    sys.argv = ['verify_whitelist_q28.py', '--out', OUT]
    try:
        m.main()
    except SystemExit:
        pass
    rep = json.load(open(OUT, encoding='utf-8'))
    if rep.get('ok') is False:
        print('NC_DETECTED (恒等归一 ⇒ ok=false, fails=%d)' % len(rep.get('fails') or []))
        return 0
    print('NC_NOT_DETECTED (恒等归一仍 ok=%s ⇒ 覆盖核验空心)' % rep.get('ok'))
    return 1


if __name__ == '__main__':
    sys.exit(main())
