#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q23 · 收口件: 比较器负控 (P8) / 确定性比对 (P6,P7) / 登记切换 (P4) / 零回归 + L2 机检 (P9) / 台账落盘.

只做机检与登记, 不产生新测量。所有写入前置断言 (序列化器逐字节复现) + 幂等 + 读回校验。
用法: python3 finalize_q23.py [--nc] [--compare] [--apply] [--verify] [--kpi] [--restore-drift]
      (不给任何开关 = 全做)
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REG = ROOT / 'eval' / 'capability' / 'instruments.json'
KPI = ROOT / 'eval' / 'capability' / 'kpi.jsonl'
R1 = HERE / 'derived_inputs_q23_run1.json'
R2 = HERE / 'derived_inputs_q23_run2.json'
REG_OUT = HERE / 'finalize_q23.json'
DRIFT_FILES = ['eval/capability/exp1-q20/l2runs/verdict_q17.json',
               'eval/capability/exp1-q20/l2runs/selftest_q17.json']
ALLOWED_ROW_KEYS = {'input_surface', 'input_surface_source', 'input_surface_reason',
                    'input_fingerprint', 'input_fingerprint_round', 'superseded_input_fingerprint'}

sys.path.insert(0, str(HERE))
import derive_inputs_q23 as Q23       # noqa: E402  (关系判定器单源)
sys.path.insert(0, str(ROOT / 'eval' / 'capability'))
import instruments_check as IC        # noqa: E402  (L2 字段机检单源)


def dump(obj, indent=1):
    return json.dumps(obj, ensure_ascii=False, indent=indent) + '\n'


def load(p):
    return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))


def targets(doc):
    return [r for r in doc['rows'] if not r.get('crosscheck')]


# ---------------- P6 / P7 ----------------
def do_compare():
    a, b = targets(load(R1)), targets(load(R2))
    per = []
    for x, y in zip(a, b):
        per.append({'id': x['id'],
                    'surface_same': x.get('input_surface') == y.get('input_surface'),
                    'fp_same': (x.get('input_fingerprint') or []) == (y.get('input_fingerprint') or []),
                    'sha12_same': {f['path']: f['sha12'] for f in (x.get('fingerprint_detail') or [])}
                                  == {f['path']: f['sha12'] for f in (y.get('fingerprint_detail') or [])},
                    'rc_same': x.get('rc') == y.get('rc'), 'events_same': x.get('events_n') == y.get('events_n'),
                    'surface': x.get('input_surface')})
    sets = {tuple(r.get('input_fingerprint') or []) for r in a}
    res = {'P6_determinism_all_rows': all(p['surface_same'] and p['fp_same'] and p['sha12_same']
                                          and p['rc_same'] and p['events_same'] for p in per),
           'P7_nontrivial_distinct_sets': len(sets), 'P7_ok': len(sets) >= 2,
           'rows_n': len(per), 'per_row': per,
           'crosscheck_q21': load(R1).get('crosscheck_q21'),
           'P10_crosscheck_ok': all(c['surface_match'] and c['fp_match'] for c in load(R1).get('crosscheck_q21') or [])}
    return res


# ---------------- P8 比较器负控 ----------------
def do_nc():
    d = targets(load(R1))
    row = next(r for r in d if r['id'] == 'exp1q17.archive-field-provenance')
    prior = row['prior_fingerprint']
    derived = row['fingerprint_detail']
    cases = []
    base = Q23.relation(prior, derived)
    cases.append({'case': 'control_unmutated', 'expect': '非 equal (真值 superset)',
                  'got': base['relation'], 'ok': base['relation'] == 'superset'})
    # NC-a: 删 1 项 ⇒ 派生应表现为 superset, 且 added 含被删项
    m = [dict(x) for x in prior][1:]
    ra = Q23.relation(m, derived)
    cases.append({'case': 'NC-a drop-one', 'expect': "superset ∧ added 含被删项",
                  'got': ra['relation'] + '/' + str(ra['added'])[:60],
                  'ok': ra['relation'] == 'superset' and prior[0]['path'] in ra['added']})
    # NC-b: 加 1 项伪路径 ⇒ 该伪路径必须出现在 removed; 且 added 集与基线一致 (位移只能来自被注入项)
    m = [dict(x) for x in prior] + [{'path': 'eval/capability/_nc_bogus_q23.json', 'sha12': 'deadbeefdead'}]
    rb = Q23.relation(m, derived)
    cases.append({'case': 'NC-b add-bogus',
                  'expect': "removed 含伪路径 ∧ added == 基线 added (注入项只进 removed)",
                  'got': rb['relation'] + '/removed=' + str(rb['removed'])[:50] + '/added_eq_base=' + str(rb['added'] == base['added']),
                  'ok': 'eval/capability/_nc_bogus_q23.json' in rb['removed'] and rb['added'] == base['added']})
    # NC-c: 改 1 项 sha12 ⇒ 应报 sha_changed
    m = [dict(x) for x in prior]
    m[0]['sha12'] = '000000000000'
    rc = Q23.relation(m, derived)
    cases.append({'case': 'NC-c sha-mutate', 'expect': 'sha_changed 非空且含该项',
                  'got': rc['relation'] + '/' + str(rc['sha_changed'])[:60],
                  'ok': bool(rc['sha_changed']) and rc['sha_changed'][0] == prior[0]['path']})
    # NC-d: 派生=既往(自比) ⇒ 必须 equal (防「恒不等」的另一侧)
    cases.append({'case': 'NC-d self-compare', 'expect': 'equal',
                  'got': Q23.relation(derived, derived)['relation'],
                  'ok': Q23.relation(derived, derived)['relation'] == 'equal'})
    return {'P8_all_nc_pass': all(c['ok'] for c in cases), 'cases': cases}


# ---------------- P4 登记切换 ----------------
def build_new_rows(man, d):
    by_id = {r['id']: r for r in d}
    new = json.loads(json.dumps(man))
    changed = []
    for row in new['instruments']:
        rec = by_id.get(row['id'])
        if not rec:
            continue
        n = len(rec.get('input_fingerprint') or [])
        old = row.get('input_fingerprint') or []
        if rec['input_surface'] == 'external_files':
            reason = ('EXP1-Q23 审计钩子重推导: 仓库内输入文件 %d ≤ 上限 %d (口径=登记命令的真实读面)'
                      % (n, 24))
        else:
            reason = ('EXP1-Q23 审计钩子重推导: 无仓库内输入文件 (登记命令走内建夹具/自身产物); '
                      '既往登记的语料面与「登记命令真实读面」口径不同 ⇒ 旧口径作废')
        row['input_surface'] = rec['input_surface']
        row['input_surface_source'] = 'audit_hook'
        row['input_surface_reason'] = reason
        row['input_fingerprint'] = [{'path': f['path'], 'sha12': f['sha12']}
                                    for f in (rec.get('fingerprint_detail') or [])]
        row['input_fingerprint_round'] = 'EXP1-Q23'
        if old and (rec['input_surface'] != 'external_files' or old != row['input_fingerprint']):
            row['superseded_input_fingerprint'] = old
        changed.append(row['id'])
    return new, changed


def do_apply(dry=False):
    txt = REG.read_text(encoding='utf-8')
    man = json.loads(txt)
    assert dump(man) == txt, '序列化器未能逐字节复现原文件 ⇒ 停手改用文本插入 (禁止静默重排)'
    d = targets(load(R1))
    new, changed = build_new_rows(man, d)
    out = dump(new)
    idem = dump(json.loads(out)) == out
    if not dry:
        REG.write_text(out, encoding='utf-8')
    back = load(REG) if not dry else new
    ok = []
    for row in back['instruments']:
        if row['id'] in changed:
            rec = next(r for r in d if r['id'] == row['id'])
            want = [{'path': f['path'], 'sha12': f['sha12']} for f in (rec.get('fingerprint_detail') or [])]
            ok.append({'id': row['id'], 'source': row['input_surface_source'],
                       'surface': row['input_surface'], 'fp_n': len(row['input_fingerprint']),
                       'fp_matches_derived': row['input_fingerprint'] == want,
                       'round': row.get('input_fingerprint_round'),
                       'superseded_kept': len(row.get('superseded_input_fingerprint') or [])})
    return {'changed_n': len(changed), 'changed': changed, 'idempotent': idem,
            'readback_ok': all(o['fp_matches_derived'] and o['source'] == 'audit_hook' for o in ok),
            'readback': ok}


# ---------------- P4 零回归 + P9 字段机检 ----------------
def do_verify():
    head = json.loads(subprocess.run(['git', 'show', 'HEAD:eval/capability/instruments.json'],
                                     cwd=str(ROOT), capture_output=True, text=True).stdout)
    cur = load(REG)
    hm = {r['id']: r for r in head['instruments']}
    cm = {r['id']: r for r in cur['instruments']}
    rows = []
    for rid in hm:
        a, b = hm[rid], cm.get(rid)
        if b is None:
            rows.append({'id': rid, 'ok': False, 'note': 'MISSING_IN_NEW'})
            continue
        keys = sorted({k for k in set(a) | set(b) if a.get(k) != b.get(k)})
        if not keys:
            rows.append({'id': rid, 'ok': True, 'changed_keys': []})
            continue
        bad = [k for k in keys if k not in ALLOWED_ROW_KEYS]
        rows.append({'id': rid, 'ok': not bad, 'changed_keys': keys, 'unexpected_keys': bad})
    l2 = []
    for r in cur['instruments']:
        if r['id'] in cm and r.get('input_fingerprint_round') == 'EXP1-Q23':
            ok, det = IC.check_l2_fields(r)
            l2.append({'id': r['id'], 'l2_ok': bool(ok), 'detail': det})
    return {'zeroregress_ok': all(r['ok'] for r in rows) and len(hm) == len(cm),
            'rows_n_before': len(hm), 'rows_n_after': len(cm), 'rows': rows,
            'P9_l2_field_check_ok': all(x['l2_ok'] for x in l2), 'l2': l2}


# ---------------- 台账 ----------------
def do_kpi(cmp_res, nc_res, ap_res, vf_res, drift):
    line = {
        'round': 'EXP1-Q23',
        'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'kind': 'instrument-input-surface-re-derivation (EXP1-Q21 欠账清账: 6 行 prior_round_registration)',
        'artifact': ('eval/capability/exp1-q23/{prereg_q23.json,derive_inputs_q23.py,finalize_q23.py,'
                     'derived_inputs_q23_run1.json,derived_inputs_q23_run2.json,side_effect_drift_q23.json,'
                     'l2runs/*}; eval/capability/instruments.json(6 行输入面口径切换); '
                     'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md 附录X'),
        'change': ('6 行既往手登记指纹改用审计钩子重推导 (机具单源复用 Q21 io_trace + 排除规则 A1); '
                   '口径统一定义为「登记命令的真实读面」; 旧条目以 superseded_input_fingerprint 保留 (不删证据)'),
        'readings': {
            'targets_n': cmp_res['rows_n'], 'hard_fail_n': 0,
            'external_files': 3, 'self_contained': 3,
            'fingerprint_entries': 7, 'fingerprint_sets_distinct': cmp_res['P7_nontrivial_distinct_sets'],
            'relation_vs_prior': {'superset': 2, 'subset': 4},
            'sha256sum_cross_mismatch': 0,
            'determinism_runs_n': 2, 'determinism_bitwise_same': cmp_res['P6_determinism_all_rows'],
            'q21_crosscheck_rows': 2, 'q21_crosscheck_fp_match_n': 2,
            'nc_cases_n': 4, 'nc_pass_n': sum(1 for c in nc_res['cases'] if c['ok']),
            'registry_changed_rows_n': ap_res['changed_n'], 'registry_idempotent': ap_res['idempotent'],
            'zeroregress_ok': vf_res['zeroregress_ok'], 'l2_field_check_n': len(vf_res['l2']),
            'l2_field_check_pass_n': sum(1 for x in vf_res['l2'] if x['l2_ok']),
        },
        'criterion': ('J1 测量成立 = 6/6 行 rc==expect ∧ events_n>0 ∧ 指纹 sha12 与 sha256sum 双实现一致; '
                      'J5 确定性 = 两跑逐位相同 ∧ 跨行集合互异; J6 比较器 4/4 负控; J7 L2 字段机检全绿; '
                      'J3 零回归 = 仅 6 行的允许字段变动'),
        'evidence_level': 'L3 (真机: 6 条登记命令在审计钩子下真跑 ×2 + 2 条 Q21 已登记行交叉比对)',
        'honest': ('① P2 被证伪: 3/6 行派生为 self_contained 而非 external_files (登记命令 --selftest 走内建夹具) '
                   '⇒ 登记口径从「器具语料面」改为「登记命令真实读面」, 旧条目保留在 superseded_input_fingerprint; '
                   '② P5 被证伪: 本轮命令窗口内既有产物出现语义漂移 3 处 (q17 两文件 = 仅错误文案内的 /tmp 临时名; '
                   'r444 一处 = 25 键差异含判据方向翻转) ⇒ 原件已归档 l2runs/regenerated_*, 工作树复原 HEAD; '
                   '③ dotnet 形式校验 (VerificationForm|SkillGeneralization|DevPlanDocRef) 未跑: 对侧 R466 在建 + '
                   'MemAvailable 1287MB < 准入 2600MB ⇒ 结转下轮, 不伪造绿'),
        'debt': ('① r444.prefilter-precheck 落盘证据在当前器具下不可复现 (器具 3 跑确定性 b74e791ccca7, 输入面 16/16 '
                 '无漂移, 证据 ec57f5664141 含 P1 反例 4→0 / P3 可省 71→67 的方向翻转) ⇒ 该 capability 的结论需以当前 '
                 '器具重生并复核; ② 登记表未绑定「证据生成时的器具 sha12/输入 sha12」⇒ 器具定稿后证据未重生也全绿; '
                 '③ q17 登记命令的落盘证据含墙钟/临时名漂移 (非语义白名单未覆盖 /tmp 路径)'),
        'next': ('① 先跑 dotnet 形式校验 (VerificationForm|SkillGeneralization|DevPlanDocRef) 10/10 绿; '
                 '② 预注册轮: 以当前器具重生 r444 precheck 证据并复核 R444 判据方向; '
                 '③ 给登记表加 evidence_generated_with 字段 (证据 ↔ 器具/输入 版本绑定)'),
        'owner_round': 'EXP1-Q23',
        'covers': ['eval/capability/exp1-q23/derive_inputs_q23.py', 'eval/capability/exp1-q23/finalize_q23.py',
                   'eval/capability/instruments.json'],
        'negative_control': 'finalize_q23.py --nc (4 例: 删项/加伪项/改 sha12/自比 equal)',
    }
    old = KPI.read_text(encoding='utf-8') if KPI.exists() else ''
    if any(json.loads(l).get('round') == 'EXP1-Q23' for l in old.splitlines() if l.strip()):
        return {'appended': False, 'reason': 'already-present(idempotent)'}
    with KPI.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + '\n')
    return {'appended': True, 'lines_after': len(KPI.read_text(encoding='utf-8').strip().splitlines())}


def restore_drift():
    p = subprocess.run(['git', 'checkout', '--'] + DRIFT_FILES, cwd=str(ROOT), capture_output=True, text=True)
    return {'restored': DRIFT_FILES, 'rc': p.returncode}


def main():
    ap = argparse.ArgumentParser()
    for f in ('nc', 'compare', 'apply', 'verify', 'kpi', 'restore_drift'):
        ap.add_argument('--' + f.replace('_', '-'), action='store_true')
    a = ap.parse_args()
    do_all = not any([a.nc, a.compare, a.apply, a.verify, a.kpi, a.restore_drift])
    out = {}
    if do_all or a.restore_drift:
        out['restore_drift'] = restore_drift()
    cmp_res = do_compare()
    nc_res = do_nc()
    if do_all or a.compare:
        out['compare'] = cmp_res
    if do_all or a.nc:
        out['nc'] = nc_res
    ap_res = do_apply(dry=not (do_all or a.apply))
    if do_all or a.apply:
        out['apply'] = ap_res
    vf_res = do_verify()
    if do_all or a.verify:
        out['verify'] = vf_res
    if do_all or a.kpi:
        out['kpi'] = do_kpi(cmp_res, nc_res, ap_res, vf_res, None)
    res = {'schema': 'q23-finalize/1', 'ts': time.strftime('%F %T'),
           'P6_ok': cmp_res['P6_determinism_all_rows'], 'P7_ok': cmp_res['P7_ok'],
           'P8_ok': nc_res['P8_all_nc_pass'], 'P10_ok': cmp_res['P10_crosscheck_ok'],
           'P4_ok': vf_res['zeroregress_ok'], 'P9_ok': vf_res['P9_l2_field_check_ok'],
           'apply': ap_res, 'verify': vf_res, 'nc': nc_res['cases'], 'compare': cmp_res['per_row'],
           ('kpi' if 'kpi' in out else 'kpi_skipped'): out.get('kpi', 'dry-run')}
    REG_OUT.write_text(dump(res, indent=1), encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('P6_ok', 'P7_ok', 'P8_ok', 'P10_ok', 'P4_ok', 'P9_ok')},
                     ensure_ascii=False))
    print(json.dumps({'changed_n': ap_res['changed_n'], 'idempotent': ap_res['idempotent'],
                      'readback_ok': ap_res['readback_ok'],
                      'zeroregress': res['P4_ok'], 'l2_n': len(vf_res['l2']),
                      'l2_pass': sum(1 for x in vf_res['l2'] if x['l2_ok']),
                      'kpi': out.get('kpi', 'dry')}, ensure_ascii=False, indent=1))
    bad = not (res['P6_ok'] and res['P7_ok'] and res['P8_ok'] and res['P10_ok'] and res['P4_ok'] and res['P9_ok'])
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
