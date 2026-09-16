#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q39 · 候选③ 的**系统级增量**: 器具声明的全表扫描重审 —— 从轮次产物升格为**常设工具**。

来源: `eval/capability/exp1-q38/refresh_manifest_decls_q38.py` (Q38 候选①的修复件)。升格理由:
提交钩子不得依赖「轮次命名目录里的产物」—— 轮次目录是证据, 常设通路要落在 `eval/capability/`。
Q38 件保留为 6 行 shim (委托本件), 使 Q38 的证据命令仍可逐字复跑, 且**只有一份实现** (无漂移)。

  * 默认 (无参) = **只读扫描**: 打印全表漂移集合 + 结论 (退出码 0 绿 / 2 漂移 / 3 格式漂移)。
  * `--apply`   = 重审刷新 (只动 version / instrument_sha12 两字段, 不重排; 写后读回复核; 幂等)。

纪律 (承「登记表程序化改写」铁律): 改写前断言「序列化器逐字节复现原文件」, 失败即拒写;
只动目标字段; 幂等; 写盘后读回比对。stdout 恒打 `DECL_SWEEP checked=<n> drifted=<n>` 机读行。
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAN = ROOT / 'eval/capability/instruments.json'


def sha12(p):
    try:
        return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:12]
    except Exception:
        return None


def sweep(man=MAN, apply=False):
    """全表扫描: version_source == content-sha12 的行逐行比对现盘 sha256[:12]。
    返回 (rc, measured, drifted)；rc: 0 无漂移 / 2 有漂移(未写) / 3 序列化器不复现(拒写)。"""
    raw = man.read_text(encoding='utf-8')
    doc = json.loads(raw)
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    tail = '\n' if raw.endswith('\n') else ''
    if ser + tail != raw:
        print('SER_ASSERT=FAIL 序列化器未能逐字节复现原文件 ⇒ 拒绝写盘 (fail-closed)')
        print('  RAWLEN=%d SERLEN=%d tail=%r' % (len(raw), len(ser), tail))
        return 3, {'checked': 0, 'drifted': 0}, []
    print('SER_ASSERT=OK (indent=1, ensure_ascii=False, tail=%s)' % ('LF' if tail else 'NONE'))

    drifted, checked = [], 0
    for e in doc['instruments']:
        if e.get('version_source') != 'content-sha12':
            continue
        checked += 1
        live = sha12(e['evidence_path'])
        before = (e.get('version'), e.get('instrument_sha12'))
        after = ('content-sha12:' + str(live), live)
        if before != after:
            drifted.append((e['id'], e['evidence_path'], before, after))
    print('DECL_SWEEP checked=%d drifted=%d' % (checked, len(drifted)))
    for tid, ep, before, after in drifted:
        print('  DRIFT %-32s %s' % (tid, ep))
        print('        before version=%s instrument_sha12=%s' % before)
        print('        after  version=%s instrument_sha12=%s' % after)
    if not drifted:
        print('DECL_SWEEP=OK (0 处漂移; 只读, 一个字节都没动)')
        return 0, {'checked': checked, 'drifted': 0}, []
    if not apply:
        print('DECL_SWEEP=DRIFT (只读模式; 加 --apply 才刷新 —— 判据未放宽, 只是把声明补齐)')
        return 2, {'checked': checked, 'drifted': len(drifted)}, drifted

    by_id = {e['id']: e for e in doc['instruments']}
    for tid, _ep, _b, (ver, isha) in drifted:
        by_id[tid]['version'] = ver
        by_id[tid]['instrument_sha12'] = isha
    out = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    with open(man, 'w', encoding='utf-8', newline='') as fh:
        fh.write(out)
    with open(man, encoding='utf-8', newline='') as fh:
        back = fh.read()
    print('WRITE_READBACK=%s' % ('OK' if back == out else 'MISMATCH'))
    if back != out:
        return 2, {'checked': checked, 'drifted': len(drifted)}, drifted
    print('RE_AUDITED=%d' % len(drifted))
    print('VERDICT=PASS (声明重审刷新完成; 判据未放宽 —— 修复前读数原样保留)')
    return 0, {'checked': checked, 'drifted': len(drifted)}, drifted


def main():
    args = sys.argv[1:]
    man = MAN
    if '--manifest' in args:
        man = pathlib.Path(args[args.index('--manifest') + 1])
    rc, _m, _d = sweep(man=man, apply=('--apply' in args))
    return rc


if __name__ == '__main__':
    sys.exit(main())
