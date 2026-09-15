#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q21 · 登记器: 把派生输入面写回 instruments.json。

纪律 (见 skill 登记表程序化改写纪律):
 1. 改写前断言「序列化器逐字节复现原文件」——不成立则拒绝改写 (改用文本插入), 绝不静默重排;
 2. 幂等: 重跑不重复插入;
 3. 读回校验: 不信工具返回, 重读文件抽查写入区域;
 4. 只写派生器实测的字段, 不手填任何 sha。
"""
import argparse
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REG = ROOT / 'eval/capability/instruments.json'
DERIVED = HERE / 'derived_inputs_q21.json'
PRIOR_SOURCE_NOTE = 'Q19/Q20 轮登记的既往指纹; 未经审计钩子重推导 (欠账, 记入下轮候选)'


def encode(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1) + '\n'


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--derived', default=str(DERIVED))
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    raw = REG.read_bytes()
    man = json.loads(raw.decode('utf-8'))
    if args.apply and encode(man).encode('utf-8') != raw:
        print('SERIALIZER-NOT-BYTE-IDENTICAL: 拒绝改写 (需改用文本插入)')
        return 2
    der = json.loads(pathlib.Path(args.derived).read_text(encoding='utf-8'))
    by_id = {r['id']: r for r in der['rows']}

    changed, skipped, pending = [], [], []
    for row in man['instruments']:
        rid = row['id']
        if rid in by_id:
            d = by_id[rid]
            surf = d.get('input_surface')
            if surf == 'undetermined':
                pending.append(rid)
                continue
            row['input_surface'] = surf
            row['input_surface_source'] = 'audit_hook'
            row['input_surface_reason'] = d.get('input_surface_reason') or ''
            row['input_surface_evidence'] = 'eval/capability/exp1-q21/derived_inputs_q21.json'
            if surf == 'dynamic_corpus':
                row['corpus_dynamic_count'] = d.get('corpus_dynamic_count')
                row.pop('input_fingerprint', None)
                row['input_fingerprint'] = []
            elif surf == 'external_files':
                detail = d.get('fingerprint_detail') or []
                row['input_fingerprint'] = [{'path': f['path'], 'sha12': f['sha12']} for f in detail]
            else:
                row['input_fingerprint'] = []
        elif row.get('input_fingerprint'):
            row.setdefault('input_surface', 'external_files')
            row['input_surface_source'] = 'prior_round_registration'
            row['input_surface_reason'] = PRIOR_SOURCE_NOTE
        else:
            pending.append(rid)
        if rid in by_id or row.get('input_surface'):
            changed.append(rid)

    out = encode(man)
    if args.apply:
        REG.write_text(out, encoding='utf-8')
    src = json.loads(REG.read_text(encoding='utf-8'))['instruments']
    n_surf = sum(1 for r in src if r.get('input_surface'))
    n_ext = sum(1 for r in src if r.get('input_surface') == 'external_files')
    n_self = sum(1 for r in src if r.get('input_surface') == 'self_contained')
    n_dyn = sum(1 for r in src if r.get('input_surface') == 'dynamic_corpus')
    n_fp = sum(len(r.get('input_fingerprint') or []) for r in src)
    back = json.loads(REG.read_text(encoding='utf-8'))
    report = {
        'apply': args.apply, 'rows_n': len(back['instruments']),
        'surface_declared': n_surf, 'external_files': n_ext, 'self_contained': n_self,
        'dynamic_corpus': n_dyn, 'fingerprint_entries': n_fp,
        'prior_round_registration': sum(1 for r in src
                                        if r.get('input_surface_source') == 'prior_round_registration'),
        'audit_hook': sum(1 for r in src if r.get('input_surface_source') == 'audit_hook'),
        'still_pending': pending, 'changed_n': len(changed),
        'readback_ok': bool(n_surf == len(back['instruments']) and not pending),
        'reg_sha256_before': sha256_bytes(raw),
        'reg_sha256_after': sha256_bytes(REG.read_bytes()) if args.apply else None,
    }
    (HERE / 'register_q21_report.json').write_text(encode(report), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report['readback_ok'] else 3


if __name__ == '__main__':
    sys.exit(main())
