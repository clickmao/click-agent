#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 候选⑤: `instruments_check.py` 面别分区 (定向运行不得覆盖全量面记录)。

缺陷 (Q25 实测): `--only <一行>` 的运行会把 18 行全量面记录 `instruments-check.json`
整体改写成 1 行 ⇒ 历史读数被静默降级 (与「器具默认 --out 指向轮次证据」同族)。
本步: face = full | scoped | negative-control 三面分区 + `--out` 显式覆盖 + 输出自带
face/only/manifest_sha12/instrument_sha12 (面别与器具版本在产物里可机检)。

幂等: 已应用则报 ALREADY_APPLIED rc=0。
"""
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TARGET = ROOT / 'eval/capability/instruments_check.py'

P = []


def add(old, new, tag):
    P.append((tag, old, new))


add('''OUT_NC_NOTAPPLIED = ROOT / 'eval/capability/instruments-check-nc-notapplied.json\'''',
    '''OUT_NC_NOTAPPLIED = ROOT / 'eval/capability/instruments-check-nc-notapplied.json'
# EXP1-Q30 (候选⑤) 面别分区 —— `--only` 定向运行**不得**覆盖全量面记录
#   (Q25 实测: 一次定向跑把 18 行全量面记录改写成 1 行, 历史读数被静默降级)。
#   三面各自固定落盘名: full / scoped / negative-control; `--out` 可显式覆盖。
OUT_SCOPED = ROOT / 'eval/capability/instruments-check-scoped.json\'''', 'outs')

add('''FACE_OUTPUTS = {'eval/capability/instruments-check.json', 'eval/capability/instruments-check-drift.json',''',
    '''FACE_OUTPUTS = {'eval/capability/instruments-check.json', 'eval/capability/instruments-check-scoped.json',
                'eval/capability/instruments-check-drift.json',''', 'whitelist')

add('''    inj_mode, target = None, OUT
    for flag, (mode, path) in INJECTS.items():
        if flag in sys.argv:
            inj_mode, target = mode, path''',
    '''    inj_mode, target = None, OUT
    for flag, (mode, path) in INJECTS.items():
        if flag in sys.argv:
            inj_mode, target = mode, path
    # EXP1-Q30: 面别解析 —— 注入模式自带命名空间; 定向模式落 scoped 面; 只有全量面写 OUT。
    face = 'negative-control' if inj_mode else ('scoped' if only else 'full')
    if inj_mode is None:
        target = OUT_SCOPED if only else OUT
    if '--out' in sys.argv:
        target = pathlib.Path(sys.argv[sys.argv.index('--out') + 1])
        if not target.is_absolute():
            target = ROOT / target''', 'face_resolve')

add('''    doc = {'schema': 'instruments-check/4', 'manifest': 'eval/capability/instruments.json',
           'l2_field_checks': True, 'input_surface_checks': True,''',
    '''    try:
        man_sha12 = hashlib.sha256(MAN.read_bytes()).hexdigest()[:12]
        self_sha12 = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:12]
    except Exception:
        man_sha12 = self_sha12 = None
    doc = {'schema': 'instruments-check/5', 'manifest': 'eval/capability/instruments.json',
           'manifest_sha12': man_sha12, 'instrument_sha12': self_sha12,
           'face': face, 'only': sorted(only) if only else None,
           'out': (str(target.relative_to(ROOT)) if str(target).startswith(str(ROOT)) else str(target)),
           'l2_field_checks': True, 'input_surface_checks': True,''', 'doc')

add('''    print(f"\\nL2 器具验收面: {len(res) - bad}/{len(res)} 通过; 落盘 {target.relative_to(ROOT)}")''',
    '''    print(f"\\nL2 器具验收面[{face}]: {len(res) - bad}/{len(res)} 通过; 落盘 {target.relative_to(ROOT)}")''',
    'print')

add('''用法: python3 eval/capability/instruments_check.py [--only id1,id2] [--fingerprint-drift-inject]''',
    '''用法: python3 eval/capability/instruments_check.py [--only id1,id2] [--out <path>] [--fingerprint-drift-inject]

面别分区 (EXP1-Q30): face=full ⇒ instruments-check.json; face=scoped (给了 --only) ⇒
instruments-check-scoped.json; face=negative-control (注入模式) 各自命名空间; `--out` 显式覆盖。''', 'usage')


def main():
    raw = TARGET.read_text(encoding='utf-8')
    if 'OUT_SCOPED' in raw and "face = 'negative-control'" in raw:
        print('ALREADY_APPLIED (幂等, rc=0); sha256[:12]=%s' % hashlib.sha256(raw.encode()).hexdigest()[:12])
        return 0
    for tag, o, n in P:
        c = raw.count(o)
        if c != 1:
            print('PATCH_FAIL %s: old 出现 %d 次 (要求 1) ⇒ 零字节写入' % (tag, c))
            return 1
        raw = raw.replace(o, n, 1)
    TARGET.write_text(raw, encoding='utf-8')
    back = TARGET.read_text(encoding='utf-8')
    assert back == raw
    import py_compile
    py_compile.compile(str(TARGET), doraise=True)
    print('APPLIED %d patches; sha256[:12]=%s' % (len(P), hashlib.sha256(back.encode()).hexdigest()[:12]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
