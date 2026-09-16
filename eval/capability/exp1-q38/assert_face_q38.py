#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q38 · 本轮预注册判据的**统一断言器** (面 + 两个负控面 + 目录结点面 + 尾契约面)。

预注册判据 (取证前写定, 见本文件与 docs/plans 的 EXP1-Q38 节):
  J1 修复前全量面 (T11, 干净窗口 21:42:56–21:47:12 无对侧在飞): rc=1 ∧ 可判据 23/25 ∧
     真红集合 == {l2.instruments-check, exp1q31.only-equivalence} ∧ 两红**仅**由声明漂移字段
     (version / instrument_sha12) 造成 ∧ 信息项 2/2 ∧ side_effects=[] ∧ gate.measurement_ok。
  J2 成员类**混合**注入面 (全量清单): rc=1 ∧ 可判据红 1 ∧ 信息项红 1 ∧ 分母 27 ∧
     inject_expect_rc=1 ∧ 注入落在该两类各一次 (injected_red 可见)。
  J3 成员类**只信息项红**面 (全量清单): rc=0 ∧ 可判据红 0 ∧ 信息项红 1 ∧ 分母 27 ∧ inject_expect_rc=0。
  J4 修复后全量面 (T14): rc=0 ∧ 可判据 25/25 ∧ 信息项 2/2 ∧ side_effects=[] ∧ face=full ∧
     gate.measurement_ok=True。
  J5 修复**定位性**: T11 与 T14 的行级差异**恰为**被修复的两行, 且这两行只差 version/instrument_sha12。
  J6 目录结点归档形态: 守恒全绿 ∧ 完整结点重跑逐结点等价 (diff=0) ∧ 非平凡 (Σn_refs>0) ∧
     清单不足负控成立 ∧ 摘文件判别力负控成立。
  J7 尾契约字段: 影子自检 7/7 ∧ 三次真实运行记录覆盖**两个**分支 (非规范 1 / 规范 2)。

三态 (承「受阻执行分级落盘」纪律): PASS / FAIL / **BLOCKED** —— 判据所需产物缺席 ⇒ BLOCKED,
**绝不**写占位 verdict, 也不把缺席读成通过。整体退出码: 有 FAIL ⇒ 2 / 全无 FAIL 有 BLOCKED ⇒ 3 / 全绿 ⇒ 0。

判别力自证 (--selftest, 影子): 对**每条**判据做一次定向篡改, 断言该判据必须翻红
(受阻塞的判据用**合成记录**证明其判别力 —— 合成不冒充真机读数, 只验判据器本身)。
"""
import copy
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CAP = ROOT / 'eval/capability'

PATHS = {
    't11': HERE / 'face_q38_t11_prefix.json',
    'rc11_log': HERE / 'logs/face_t11_prefix_runner.txt',
    't12': CAP / 'instruments-check-class-mixed.json',
    't13': CAP / 'instruments-check-class-info-only.json',
    't12_log': pathlib.Path('/tmp/q38_t12b.stdout'),
    't13_log': pathlib.Path('/tmp/q38_t13b.stdout'),
    't14': HERE / 'face_q38_t14.json',
    't14_log': pathlib.Path('/tmp/q38_t14.stdout'),
    'dirs': HERE / 'archive_dir_nodes_q38.json',
    'tail': HERE / 'bind_evidence_tail_selftest_q38.json',
    'rr_a': HERE / 'bind_evidence_run_record_q38.json',
    'rr_b': HERE / 'bind_evidence_run_record_q38_b.json',
    'rr_c': HERE / 'bind_evidence_run_record_q38_c.json',
}
FIXED_ROWS = ('l2.instruments-check', 'exp1q31.only-equivalence')


def _json(p):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
    except Exception:
        return None


def _rc(p):
    try:
        txt = pathlib.Path(p).read_text(encoding='utf-8', errors='replace')
    except Exception:
        return None
    m = re.findall(r'\bRC_[A-Za-z0-9_]+=(\d+)', txt)
    return int(m[-1]) if m else None


def collect():
    a = {k: _json(p) for k, p in PATHS.items() if not k.endswith('_log')}
    a['rc11'] = _rc(PATHS['rc11_log'])
    a['rc12'] = _rc(PATHS['t12_log'])
    a['rc13'] = _rc(PATHS['t13_log'])
    a['rc14'] = _rc(PATHS['t14_log'])
    return a


def rows_by_id(rec):
    return {r['id']: r for r in (rec or {}).get('results', [])}


def j1(a):
    r = a['t11']
    if r is None or a['rc11'] is None:
        return 'BLOCKED', 'T11 记录/rc 缺席'
    reds = sorted(x['id'] for x in r['results'] if not x['pass'] and x['member_class'] != 'informational')
    bad_fields = {}
    for x in r['results']:
        if not x['pass']:
            bad_fields[x['id']] = sorted(k for k, v in x['l2_fields'].items() if not str(v).startswith('ok'))
    only_decl = all(set(v) <= {'version', 'instrument_sha12'} for v in bad_fields.values())
    ok = (a['rc11'] == 1 and r['passable_passed'] == 23 and r['passable_total'] == 25
          and reds == sorted(FIXED_ROWS) and only_decl
          and r['member_class']['informational_passed'] == 2 and r['member_class']['informational_total'] == 2
          and r.get('side_effects') == [] and r['side_effect_attribution']['measurement_ok'] is True)
    return ('PASS' if ok else 'FAIL',
            'rc=%s 可判据 %s/%s 红=%s 仅声明漂移=%s 信息项 %s/%s side_effects=%s'
            % (a['rc11'], r['passable_passed'], r['passable_total'], reds, only_decl,
               r['member_class']['informational_passed'], r['member_class']['informational_total'],
               r.get('side_effects')))


def _nc_judge(a, key, rc_key, want_rc, want_p, want_i):
    r = a[key]
    if r is None or a[rc_key] is None:
        return 'BLOCKED', '%s 记录/rc 缺席 (对侧在飞 ⇒ 本面未跑)' % key
    if 'inject_expect_rc' not in r:
        # 命名空间里只有**前缀**读数: 它由早于 inject_expect_rc 字段的仪器修订产出, 且窗口与对侧在飞重叠
        #   ⇒ 不能当预注册产物用。判 BLOCKED (缺席), 不判 FAIL —— 「没测到」≠「测过判红」。
        return 'BLOCKED', ('仅存前缀读数 (仪器修订早于 inject_expect_rc 字段 ∧ 窗口与对侧在飞重叠) '
                           '⇒ 干净面未跑, 不用作判据')
    mc = r['member_class']
    inj = sorted({x.get('injected_red') for x in r['results'] if x.get('injected_red')})
    ok = (a[rc_key] == want_rc and mc['passable_failed'] == want_p and mc['informational_failed'] == want_i
          and mc['total'] == 27 and r.get('inject_expect_rc') == want_rc
          and len(inj) == (1 if want_p == 0 else 2))
    return ('PASS' if ok else 'FAIL',
            'rc=%s 可判据红=%s 信息项红=%s 分母=%s expect_rc=%s 注入=%s'
            % (a[rc_key], mc['passable_failed'], mc['informational_failed'], mc['total'],
               r.get('inject_expect_rc'), inj))


def j4(a):
    r = a['t14']
    if r is None or a['rc14'] is None:
        return 'BLOCKED', 'T14 记录/rc 缺席 (对侧在飞 ⇒ 修复后全量面未跑)'
    mc = r['member_class']
    ok = (a['rc14'] == 0 and mc['passable_passed'] == 25 and mc['passable_total'] == 25
          and mc['informational_passed'] == 2 and mc['informational_total'] == 2
          and r.get('side_effects') == [] and r.get('face') == 'full' and r.get('only') is None
          and r['side_effect_attribution']['measurement_ok'] is True)
    return ('PASS' if ok else 'FAIL',
            'rc=%s 可判据 %s/%s 信息项 %s/%s side_effects=%s face=%s'
            % (a['rc14'], mc['passable_passed'], mc['passable_total'],
               mc['informational_passed'], mc['informational_total'], r.get('side_effects'), r.get('face')))


def j5(a):
    if a['t11'] is None or a['t14'] is None:
        return 'BLOCKED', 'T11 或 T14 缺席'
    r11, r14 = rows_by_id(a['t11']), rows_by_id(a['t14'])
    if set(r11) != set(r14):
        return 'FAIL', '行集不同'
    diff = [i for i in sorted(r11) if r11[i].get('pass') != r14[i].get('pass')]
    field_diff = {}
    for i in sorted(r11):
        d = sorted(k for k in set(list(r11[i].get('l2_fields', {})) + list(r14[i].get('l2_fields', {})))
                   if r11[i].get('l2_fields', {}).get(k) != r14[i].get('l2_fields', {}).get(k))
        if d:
            field_diff[i] = d
    ok = (sorted(diff) == sorted(FIXED_ROWS)
          and set(field_diff) <= set(FIXED_ROWS)
          and all(set(v) <= {'version', 'instrument_sha12', 'INJECTED'} for v in field_diff.values()))
    return ('PASS' if ok else 'FAIL', 'pass 翻转行=%s 字段差=%s' % (diff, field_diff))


def j6(a):
    d = a['dirs']
    if d is None:
        return 'BLOCKED', '目录结点面读数缺席'
    cons = d.get('conservation', {})
    ok = (all(cons.values()) and d.get('equivalence_face_nonzero_n') and
          not d.get('rerun_equivalence_diff') and not d.get('listonly_violations') and
          (d.get('negative_control_remove_file') or {}).get('detects') is True)
    return ('PASS' if ok else 'FAIL',
            '分母=%s 处置=%s 等价面=%s(非零 %s) diff=%s 清单不足违规=%s 摘文件负控=%s'
            % (d.get('denominator'), d.get('by_disposition'), d.get('equivalence_face_n'),
               d.get('equivalence_face_nonzero_n'), len(d.get('rerun_equivalence_diff') or []),
               len(d.get('listonly_violations') or []),
               (d.get('negative_control_remove_file') or {}).get('detects')))


def j7(a):
    t = a['tail']
    if t is None:
        return 'BLOCKED', '尾契约影子自检缺席'
    rrs = [a['rr_a'], a['rr_b'], a['rr_c']]
    if any(x is None for x in rrs):
        return 'BLOCKED', '运行记录不齐 (需 3 份)'
    flags = [b['noncanonical_input'] for b in rrs]
    reasons = [b['noncanonical_reason'] for b in rrs]
    ok = (all(t['checks'].values()) and t['verdict'] == 'PASS'
          and flags == [True, False, False] and reasons[0] == 'tail_lf_missing'
          and reasons[1] is None and reasons[2] is None
          and all(b['rc'] == 0 for b in rrs))
    return ('PASS' if ok else 'FAIL',
            '自检 checks=%s 真实运行 flags=%s reasons=%s' % (t.get('verdict'), flags, reasons))


JUDGES = [('J1_pre_fix_full_face', j1), ('J2_mixed_inject_full_list_red', lambda a: _nc_judge(a, 't12', 'rc12', 1, 1, 1)),
          ('J3_info_only_full_list_green', lambda a: _nc_judge(a, 't13', 'rc13', 0, 0, 1)),
          ('J4_post_fix_full_face', j4), ('J5_fix_localization', j5),
          ('J6_dir_node_archive_form', j6), ('J7_tail_contract_field', j7)]


def evaluate(a):
    return {name: fn(a) for name, fn in JUDGES}


def selftest(a):
    """影子自检: 每条判据配一次定向篡改, 断言该判据不再为 PASS (受阻塞者用合成记录)。"""
    base = copy.deepcopy(a)
    # 受阻塞判据的合成记录 (只用于验判据器判别力, 不冒充真机读数)
    if base['t12'] is None:
        base['t12'] = {'member_class': {'passable_failed': 1, 'informational_failed': 1, 'total': 27},
                       'inject_expect_rc': 1, 'results': [{'id': 'x', 'injected_red': 'class-mixed:passable'},
                                                          {'id': 'y', 'injected_red': 'class-mixed:informational'}]}
        base['rc12'] = 1
    if base['t13'] is None:
        base['t13'] = {'member_class': {'passable_failed': 0, 'informational_failed': 1, 'total': 27},
                       'inject_expect_rc': 0, 'results': [{'id': 'y', 'injected_red': 'class-info-only:informational'}]}
        base['rc13'] = 0
    if base['t14'] is None:
        base['t14'] = {'member_class': {'passable_passed': 25, 'passable_total': 25,
                                        'informational_passed': 2, 'informational_total': 2},
                       'side_effects': [], 'face': 'full', 'only': None,
                       'side_effect_attribution': {'measurement_ok': True},
                       'results': copy.deepcopy(base['t11']['results']) if base['t11'] else []}
        for r in base['t14']['results']:
            if r['id'] in FIXED_ROWS:
                r['pass'] = True
                r['l2_fields'] = {k: ('ok' if k in ('version', 'instrument_sha12') else v)
                                  for k, v in r['l2_fields'].items()}
        base['rc14'] = 0
        base['_synth_t14'] = True
    m = {}
    t = copy.deepcopy(base)
    t['t11']['passable_passed'] = 25
    m['M1_t11_denominator'] = evaluate(t)['J1_pre_fix_full_face'][0] != 'PASS'
    t = copy.deepcopy(base)
    t['t11']['side_effects'] = ['x']
    m['M2_t11_side_effects'] = evaluate(t)['J1_pre_fix_full_face'][0] != 'PASS'
    t = copy.deepcopy(base)
    t['rc12'] = 0
    m['M3_mixed_rc'] = evaluate(t)['J2_mixed_inject_full_list_red'][0] != 'PASS'
    t = copy.deepcopy(base)
    t['t12']['member_class']['passable_failed'] = 0
    m['M4_mixed_swallowed_real_red'] = evaluate(t)['J2_mixed_inject_full_list_red'][0] != 'PASS'
    t = copy.deepcopy(base)
    t['t13']['member_class']['passable_failed'] = 1
    m['M5_info_only_leaked_red'] = evaluate(t)['J3_info_only_full_list_green'][0] != 'PASS'
    t = copy.deepcopy(base)
    t['t14']['member_class']['informational_passed'] = 1
    m['M6_final_info_regressed'] = evaluate(t)['J4_post_fix_full_face'][0] != 'PASS'
    t = copy.deepcopy(base)
    if t['t14']:
        for r in t['t14']['results']:
            if r['id'] not in FIXED_ROWS:
                r['pass'] = not r['pass']
                break
    m['M7_fix_not_localized'] = evaluate(t)['J5_fix_localization'][0] != 'PASS'
    t = copy.deepcopy(base)
    t['dirs']['conservation']['c4_listonly_insufficient'] = False
    m['M8_dir_node_c4'] = evaluate(t)['J6_dir_node_archive_form'][0] != 'PASS'
    t = copy.deepcopy(base)
    t['rr_c']['noncanonical_input'] = True
    m['M9_tail_flag_constant'] = evaluate(t)['J7_tail_contract_field'][0] != 'PASS'
    print('SELFTEST %s' % json.dumps(m, ensure_ascii=False))
    print('MUTATIONS_CAUGHT=%d/%d' % (sum(1 for v in m.values() if v), len(m)))
    return 0 if all(m.values()) else 2


def main():
    a = collect()
    res = evaluate(a)
    out = {'round': 'EXP1-Q38', 'schema': 'q38-assertions/1',
           'artifacts_present': {k: (v is not None) for k, v in a.items()},
           'judgments': {k: {'status': v[0], 'detail': v[1]} for k, v in res.items()}}
    st = [v[0] for v in res.values()]
    out['verdict'] = ('FAIL' if 'FAIL' in st else ('EXECUTION_BLOCKED' if 'BLOCKED' in st else 'PASS'))
    out['counts'] = {'pass': st.count('PASS'), 'fail': st.count('FAIL'), 'blocked': st.count('BLOCKED')}
    (HERE / 'assert_face_q38.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n',
                                               encoding='utf-8')
    for k, v in res.items():
        print('%-32s %-8s %s' % (k, v[0], v[1]))
    print('VERDICT=%s counts=%s out=assert_face_q38.json' % (out['verdict'], out['counts']))
    if '--selftest' in sys.argv:
        return selftest(a)
    return {'PASS': 0, 'EXECUTION_BLOCKED': 3, 'FAIL': 2}[out['verdict']]


if __name__ == '__main__':
    sys.exit(main())
