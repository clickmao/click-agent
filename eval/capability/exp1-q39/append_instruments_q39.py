#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q39 · 候选②: 把 Q38 的两件器具登记进 L2 器具面 (instruments.json 27 → 29 行)。

  * `exp1q38.dir-node-archive`   —— 目录结点归档器 (29 结点受限内容副本 + 等价面判据)
  * `exp1q38.tail-contract-selftest` —— 尾契约字段的影子自检 (成对判据 7 项)

两行各带 `expect_rc`/`expect_substr` 与**负控**(Q39 新写的判别力自证: 把被测组件置空/置常量 ⇒
该器具必须判红)。登记纪律 (承 R409 程序化改写铁律): ① 写前断言序列化器逐字节复现原文件;
② 只追加行, 不重排; ③ 幂等 (id 已存在即跳过); ④ 写后读回校验。

用法: python3 eval/capability/exp1-q39/append_instruments_q39.py [--apply]
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MAN = ROOT / 'eval/capability/instruments.json'


def sha12(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:12]


def rows():
    a = 'eval/capability/exp1-q38/archive_dir_nodes_q38.py'
    b = 'eval/capability/exp1-q38/selftest_bind_evidence_tail_q38.py'
    return [
        {
            'id': 'exp1q38.dir-node-archive',
            'kind': 'prober',
            'cmd': 'python3 %s' % a,
            'expect_rc': 0,
            'expect_substr': 'VERDICT=PASS',
            'nc_cmd': 'python3 eval/capability/exp1-q39/_nc_dir_node_archive_q39.py',
            'nc_expect': 'detect:NC_DETECTED',
            'kpi_quad': {'单位': '结点', '分母': 'Q37 disposition=directory_node 的结点 (29)',
                         '真值源': '归档副本重跑抽取 vs Q37 现场读数',
                         '口径档': '受限内容副本 (逐文件 256 KiB / 逐结点 1 MiB)'},
            'owner_round': 'EXP1-Q38',
            'evidence_path': a,
            'version': 'content-sha12:' + sha12(a),
            'version_source': 'content-sha12',
            'instrument_sha12': sha12(a),
            'input_fingerprint': [],
            'input_surface': 'dynamic_corpus',
            'input_surface_source': 'audit_hook',
            'input_surface_reason': ('输入 = Q37 记录的 29 个结点 + 这些结点**当前盘面**的目录树 '
                                     '(随环境变化; 归档产物本身是输出, 不是输入) ⇒ 不做字节指纹, 记结点数'),
            'corpus_dynamic_count': 29,
        },
        {
            'id': 'exp1q38.tail-contract-selftest',
            'kind': 'checker',
            'cmd': 'python3 %s' % b,
            'expect_rc': 0,
            'expect_substr': 'VERDICT=PASS',
            'nc_cmd': 'python3 eval/capability/exp1-q39/_nc_tail_selftest_hollow_q39.py',
            'nc_expect': 'detect:NC_DETECTED',
            'kpi_quad': {'单位': '用例', '分母': '成对判据 7 项 (c1..c7)',
                         '真值源': '被测工具运行记录 (--run-record) 的一等字段',
                         '口径档': '规范形 / 非规范形 双跑'},
            'owner_round': 'EXP1-Q38',
            'evidence_path': b,
            'version': 'content-sha12:' + sha12(b),
            'version_source': 'content-sha12',
            'instrument_sha12': sha12(b),
            'input_fingerprint': [],
            'input_surface': 'dynamic_corpus',
            'input_surface_source': 'audit_hook',
            'input_surface_reason': ('输入 = 被测工具 + 登记表 scratch 副本 (每次运行在 /tmp 重建, '
                                     '其字节随登记表增长而变) ⇒ 不做字节指纹, 记运行次数'),
            'corpus_dynamic_count': 3,
        },
    ]


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
    before = len(doc['instruments'])
    have = {e['id'] for e in doc['instruments']}
    add = [r for r in rows() if r['id'] not in have]
    print('ROWS %d -> %d (新增 %d, 幂等跳过 %d)' % (before, before + len(add), len(add),
                                                    len(rows()) - len(add)))
    for r in add:
        print('  ADD %-34s rc=%s nc=%s surface=%s' % (r['id'], r['expect_rc'], r['nc_expect'],
                                                      r['input_surface']))
    if not apply:
        print('DRY_RUN (加 --apply 才写盘)')
        return 0
    if not add:
        print('IDEMPOTENT=OK (无新增)')
        return 0
    doc['instruments'].extend(add)
    out = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    with open(MAN, 'w', encoding='utf-8', newline='') as fh:
        fh.write(out)
    with open(MAN, encoding='utf-8', newline='') as fh:
        back = fh.read()
    print('WRITE_READBACK=%s' % ('OK' if back == out else 'MISMATCH'))
    if back != out:
        return 2
    chk = json.loads(back)
    got = [e['id'] for e in chk['instruments']]
    ok = len(got) == before + len(add) and all(r['id'] in got for r in add)
    print('READBACK_ROWS=%d ok=%s' % (len(got), ok))
    print('VERDICT=%s' % ('PASS' if ok else 'FAIL'))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
