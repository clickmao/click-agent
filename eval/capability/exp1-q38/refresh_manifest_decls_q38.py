#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q38 · 候选①的**修复件 + 系统级增量**: 器具声明的**全表扫描重审** (默认 dry-run, `--apply` 才写)。

原版只刷两个硬编码目标 ⇒ 漏掉了第三处 (manifest 行 `bind_evidence.check` 的 `evidence_path` 就是
`eval/capability/bind_evidence.py` 本身) —— 同一种缺陷在同轮内二次复现, 正是「硬编码清单」的通病。
本版改为**扫描全表**: 凡 `version_source == content-sha12` 的行, 逐行比对
`version` / `instrument_sha12` 与现盘 `evidence_path` 的 sha256[:12]; 漂移者即候选。

  * 默认 (无参) = **只读扫描**: 打印全表漂移集合 + 结论 (可用于提交钩子/轮内自检)。
  * `--apply`   = 重审刷新 (只动这两字段, 不重排; 写后读回复核; 幂等)。

纪律 (承「登记表程序化改写」铁律): 改写前断言「序列化器逐字节复现原文件」, 失败即拒绝写盘;
只动目标字段; 幂等; 写盘后读回比对。

同时报告**输入形态** (`registry` 尾 LF): 尾 LF 缺失 ⇒ 面内 `exp1q31.only-equivalence` 的
P0/P1 必红 (设计如此, 归属到输入形态, 不是通路分歧) ⇒ 本件顺带做规范化修复。
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
MAN = ROOT / 'eval/capability/instruments.json'


def sha12(p):
    try:
        return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:12]
    except Exception:
        return None


def main():
    apply = '--apply' in sys.argv
    raw = MAN.read_text(encoding='utf-8')
    doc = json.loads(raw)
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    tail = '\n' if raw.endswith('\n') else ''
    if ser + tail != raw:
        print('SER_ASSERT=FAIL 序列化器未能逐字节复现原文件 ⇒ 拒绝写盘 (fail-closed)')
        print('  RAWLEN=%d SERLEN=%d tail=%r' % (len(raw), len(ser), tail))
        return 3
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
        print('DECL_SWEEP=OK (0 处漂移; 无参模式为只读, 一个字节都没动)')
        return 0
    if not apply:
        print('DECL_SWEEP=DRIFT (只读模式; 加 --apply 才刷新 —— 判据未放宽, 只是把声明补齐)')
        return 2

    by_id = {e['id']: e for e in doc['instruments']}
    for tid, _ep, _b, (ver, isha) in drifted:
        by_id[tid]['version'] = ver
        by_id[tid]['instrument_sha12'] = isha
    out = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    with open(MAN, 'w', encoding='utf-8', newline='') as fh:
        fh.write(out)
    with open(MAN, encoding='utf-8', newline='') as fh:
        back = fh.read()
    print('WRITE_READBACK=%s' % ('OK' if back == out else 'MISMATCH'))
    if back != out:
        return 2
    print('RE_AUDITED=%d' % len(drifted))
    print('VERDICT=PASS (声明重审刷新完成; 判据未放宽 —— 修复前读数原样保留)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
