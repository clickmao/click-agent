#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q42 · 回放归档的**输入不变**证据件 (替代含 HEAD 字段的 classified 归档作 pin)。

发现 (M2 取证时自捕): `replay_q41_scopeA_classified.json` 含 HEAD 相关字段 (`head_ct` /
`post_contract_window.*`) ⇒ **每次重跑字节必变** ⇒ 不可作冻结 pin 的证据件 (会被下一次
`bind_evidence --check` 记成 FROZEN_EVIDENCE_DRIFT)。修法 = 证据取**输入不变**的归档
(`replay_q41_scopeA.json`) + 一个**确定性校验器** (本件): 只读冻结字节, 不读 HEAD, 不含时间戳。

判据 (全部机检):
  V1 scopeA 违规 37 条 ∧ **原因码集合只有 1 种** `tail_lf_missing` (⇒ 「合法但含标记」误报 0 的依据)。
  V2 scopeA 覆盖读数 146 提交 / 232 blob 与 AN.8 一致 (不得静默缩小总体)。
  V3 scopeB 扩面决议 `BROADEN_REJECTED` ∧ 命中率 0.595 > 阈 0.02 ∧ 违规 1405 / 文本 blob 4529。
  V4 判定器判别力对照 (`judge_function_control`) 对 canonical/missing/bom/crlf/empty 各有独立读数。
  V5 pin_kind 普查 (H5) 记录在案 (非缺省取值仅 1 种 ⇒ 扩面排除项)。
  V6 本件输出**确定性**: 同一输入重算两遍字节相同。
退出码: 0 全绿 / 2 判据红 / 3 环境不可判。
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
ARCH_A = ROOT / 'eval/capability/exp1-q41/replay_q41_scopeA.json'
ARCH_B = ROOT / 'eval/capability/exp1-q41/replay_q41.json'
OUT = ROOT / 'eval/capability/exp1-q42/replay_archive_verify_q42.json'


def sha16(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def build(neg=False):
    A = json.loads(ARCH_A.read_text(encoding='utf-8'))
    B = json.loads(ARCH_B.read_text(encoding='utf-8'))
    if neg:
        # EXP1-Q43 入面负控: 只篡改 **V1 依赖的输入**（把一条违规行的原因码换成
        # 「合法但含标记」的伪原因码）⇒ V1 必须转红。只动 V1 的输入、不越界动其它检查，
        # 以证明「V1 有牙」而不是「整件被弄坏」（后者会让负控变成恒真）。
        rows0 = A.get('violation_rows') or []
        if rows0:
            rows0[0]['why'] = 'false_positive_marker_present'
    rows = A['violation_rows']
    why = sorted({r['why'] for r in rows})
    tgt = set(A.get('targets') or [])
    checks, detail = {}, {}
    checks['V1_scopeA_single_reason_no_false_positive'] = (
        A['violations'] == 37 and len(rows) == 37 and why == ['tail_lf_missing']
        and all(r['path'] in tgt for r in rows))
    detail['V1'] = {'violations': A['violations'], 'rows': len(rows), 'reason_codes': why,
                    'paths_in_targets': all(r['path'] in tgt for r in rows)}

    checks['V2_scopeA_population_not_shrunk'] = (A['commits_touching'] == 146 and A['blobs_judged'] == 232)
    detail['V2'] = {'commits_touching': A['commits_touching'], 'blobs_judged': A['blobs_judged'],
                    'missing_path_in_commit': A['missing_path_in_commit']}

    h2 = B['H2_scopeB_broaden_cost']['reading']
    checks['V3_scopeB_broaden_rejected'] = (B['H2_scopeB_broaden_cost']['verdict'] == 'BROADEN_REJECTED'
                                            and h2['commit_hit_rate'] > 0.02
                                            and h2['violations'] == 1405 and h2['text_blobs_judged'] == 4529)
    detail['V3'] = {k: h2[k] for k in ('scope', 'commits_scanned', 'text_blobs_judged', 'violations',
                                       'commits_with_violation', 'commit_hit_rate')}

    jc = B['judge_function_control']['readings']
    checks['V4_judge_has_discrimination'] = (jc['canonical'][0] is True and jc['canonical'][1] is None
                                            and jc['tail_missing'] == [False, 'tail_lf_missing']
                                            and {jc['bom'][1], jc['crlf'][1], jc['empty'][1]} == {
                                                'bom_present', 'crlf_present', 'empty_or_unresolved'})
    detail['V4'] = jc

    h5 = B['H5_pin_kind_census']['reading']
    checks['V5_pin_kind_census_recorded'] = (h5['non_default_kinds'] == ['semantic-projection']
                                            and h5['negative_control']['census_changed'] is True)
    detail['V5'] = {'rows': h5['rows'], 'census': h5['census'], 'measurable_objects': h5['measurable_objects_for_AN7_3']}

    payload = {
        'schema': 'replay-archive-verify-q42/1', 'round': 'EXP1-Q42',
        'inputs': {'eval/capability/exp1-q41/replay_q41_scopeA.json': sha16(ARCH_A),
                   'eval/capability/exp1-q41/replay_q41.json': sha16(ARCH_B)},
        'inputs_note': '只读冻结归档字节; 不读 HEAD, 不含时间戳 ⇒ 输出可逐字节复现',
        'checks': checks, 'detail': detail,
        'verdict': 'PASS' if all(checks.values()) else 'FAIL',
    }
    return payload


def main():
    if not (ARCH_A.exists() and ARCH_B.exists()):
        print('ENV: 归档缺失 ⇒ 弃权 (rc=3)')
        return 3
    if '--neg-control' in sys.argv:
        # EXP1-Q43 入面负控臂: 不写 OUT（面跑侧写 = 副作用）。语义 = 篡改**被捕获**才退非零；
        # 篡改未被判红 ⇒ 退 0 ⇒ 面侧 `nc_expect:nonzero` 判红（负控不可空心）。
        np_ = build(neg=True)
        red = sorted([k for k, v in np_['checks'].items() if not v])
        caught = (np_['verdict'] == 'FAIL'
                  and red == ['V1_scopeA_single_reason_no_false_positive'])
        print('NC_TAMPER=V1_reason_code red_checks=%s' % (red,))
        print('NC_DETECTED' if caught else 'NC_HOLLOW: 篡改未被判红 ⇒ V1 是空心门')
        return 2 if caught else 0
    p1 = build()
    p2 = build()
    det = json.dumps(p1, ensure_ascii=False, indent=1, sort_keys=True) == json.dumps(p2, ensure_ascii=False,
                                                                                     indent=1, sort_keys=True)
    p1['checks']['V6_output_deterministic'] = det
    ok = all(p1['checks'].values())
    p1['verdict'] = 'PASS' if ok else 'FAIL'
    text = json.dumps(p1, ensure_ascii=False, indent=1, sort_keys=True) + '\n'
    OUT.write_text(text, encoding='utf-8')
    back = OUT.read_text(encoding='utf-8')
    rb = (back == text)
    for k in sorted(p1['checks']):
        print('%-46s %s' % (k, 'PASS' if p1['checks'][k] else 'FAIL'))
    print('READBACK=%s VERDICT=%s out=%s' % ('OK' if rb else 'FAIL', p1['verdict'], OUT))
    return 0 if (ok and rb) else 2


if __name__ == '__main__':
    sys.exit(main())
