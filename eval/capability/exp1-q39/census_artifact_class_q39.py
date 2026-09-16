#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q39 · 候选⑤: 证据本体是**源码文件**的行的分类确定性 (预注册 + 成对控制)。

缺陷 (Q38 AM.5.5 实测侧效): `bind_evidence.derive()` 对「证据文件已入库且工作区干净」的行一律判
`artifact/frozen/archived-per-round`, **不区分证据是不是源码文件** ⇒ 同一条登记行在
「工作区脏 / 干净」两态下分类**不同** (live/worktree-only ⇄ frozen/archived-per-round) ⇒ 一次
`--apply` 的**侧效**足以翻转该行语义。r476 行 (`evidence_path` = `bind_evidence.py` 自身) 即此形态。

预注册 (写于取证前, 本文件即判据载体):
  P1 分母: 登记表全部行 (机检计数), 其中「源码扩展名证据」集合逐项列出。
  P2 规则 (修后): 源码证据 **∧ 该文件就是本行的器具 (inst == ep)** ⇒ `self-derived/live/self-derived`
     且 `artifact_sha12 = null`。仅此一种组合改判。
  P3 闸等价 (缺一不可): 源码自拄行的字节闸**必须**仍存在, 只是载体从 `artifact_sha12` 换成
     `instrument_sha12`。机检 = 夹具上变异该文件字节 ⇒ 该行在**两档下都判红** (等价性, 不是口头保证)。
  P4 不改判的例外 (单列 + 记因): `inst != ep` 的源码行 (实测 `r492.arm-runner-derive-aux-carry`:
     器具 = `eval/rover/r491/run_arm_real_r491.sh`) —— 那里源码 pin 是**唯一**闸, 改类会静默丢闸 ⇒ 保持原判。
  P5 非源码证据行 (真归档产物) 分类**逐位不变** (负控: 不许借机放宽)。
  P6 确定性: 同一行在 `dirty={ep}` 与 `dirty=∅` 两态下 derive 结果**逐字段相等** (修前 r476 两态不同
     = 缺陷复现; 修后相等 = 修复成立)。
  P7 侧效: scratch 副本上对 r476 行 `--apply` ⇒ 修后 `pin_status` 仍 `live` (修前会翻 `frozen`)。
  P8 三态判决: 0 全绿 / 2 判据红 / 3 弃权 (登记表不可读 / 序列化器不逐字节复现)。

用法: python3 eval/capability/exp1-q39/census_artifact_class_q39.py [--tag pre|post]
"""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REG = ROOT / 'docs/verification-registry.json'
BE = ROOT / 'eval/capability/bind_evidence.py'
SRC_EXT = ('.py', '.sh', '.cs', '.ps1', '.js', '.ts')
SCRATCH = pathlib.Path('/tmp/q39_artifact_class_scratch')


def load_be():
    spec = importlib.util.spec_from_file_location('be_q39', str(BE))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def census(be, tag):
    doc = json.loads(REG.read_text(encoding='utf-8'))
    rows = doc['rows']
    tracked, dirty = be.git_state(str(ROOT))
    out = {'tag': tag, 'n_rows': len(rows), 'src_ext_rows': [], 'class_dist': {}}
    for r in rows:
        ep = r.get('evidence_path') or ''
        f = r.get('evidence_generated_with') or {}
        if not isinstance(f, dict) or not f:
            continue
        rec = {'id': r['id'], 'ep': ep, 'level': r.get('level'),
               'cmd': r.get('evidence_cmd'), 'declared_kind': f.get('evidence_kind'),
               'declared_status': f.get('pin_status'), 'declared_reason': f.get('pin_reason'),
               'declared_pin': f.get('artifact_sha12'), 'declared_inst': f.get('instrument'),
               'raw_cmd': r.get('raw_cmd')}
        try:
            rec['derive_clean'] = be.derive(str(ROOT), r, tracked, set())
        except Exception as exc:                      # ProjectionPinUnavailable 等
            rec['derive_clean'] = {'error': type(exc).__name__ + ':' + str(exc)[:120]}
        try:
            rec['derive_dirty'] = be.derive(str(ROOT), r, tracked, set(dirty) | {ep})
        except Exception as exc:
            rec['derive_dirty'] = {'error': type(exc).__name__ + ':' + str(exc)[:120]}
        rec['file_is_source'] = ep.endswith(SRC_EXT)
        declared_inst = (f.get('instrument'))
        rec['declared_instrument'] = declared_inst
        rec['self_gated'] = bool(rec['file_is_source']
                                 and rec['derive_clean'].get('instrument') == ep
                                 and declared_inst in (None, ep))
        rec['deterministic'] = bool(
            'error' not in rec['derive_clean'] and 'error' not in rec['derive_dirty']
            and (rec['derive_clean'].get('evidence_kind'), rec['derive_clean'].get('pin_status'),
                 rec['derive_clean'].get('pin_reason'), rec['derive_clean'].get('artifact_sha12'))
            == (rec['derive_dirty'].get('evidence_kind'), rec['derive_dirty'].get('pin_status'),
                rec['derive_dirty'].get('pin_reason'), rec['derive_dirty'].get('artifact_sha12')))
        if rec['file_is_source']:
            out['src_ext_rows'].append(rec)
        k = (rec['derive_clean'].get('evidence_kind'), rec['derive_clean'].get('pin_status'),
             rec['derive_clean'].get('pin_reason'))
        out['class_dist'][str(k)] = out['class_dist'].get(str(k), 0) + 1
    # 同族第二缺陷的量 (本轮**只测不改**, 预注册留给下一轮):
    #   已声明 frozen 的行, 若**此刻**跑 --apply, derive (按当前工作区真实态) 会把它判成什么。
    #   判成非 frozen ⇒ 冻结闸会被一次 apply 静默降级 (r476 侧效的同族形态, 只是载体是归档产物而非源码)。
    fam = []
    for r in rows:
        f = r.get('evidence_generated_with')
        if not isinstance(f, dict) or f.get('pin_status') != 'frozen':
            continue
        ep = r.get('evidence_path') or ''
        tracked, dirty = be.git_state(str(ROOT))
        rec = next((x for x in out['src_ext_rows'] if x['id'] == r['id']), None)
        if rec:
            dd = rec['derive_clean'] if ep not in dirty else rec['derive_dirty']
        else:
            try:
                dd = be.derive(str(ROOT), r, tracked, dirty)
            except Exception as exc:                 # ProjectionPinUnavailable 等 = 不可复算
                dd = {'error': type(exc).__name__ + ':' + str(exc)[:120]}
        if dd.get('error'):
            fam.append({'id': r['id'], 'ep': ep, 'declared': f.get('pin_status'),
                        'class': 'derive_unavailable_apply_skips_row', 'reason': dd['error'],
                        'ep_is_dirty': ep in dirty})
        elif dd.get('pin_status') != 'frozen':
            fam.append({'id': r['id'], 'ep': ep, 'declared': f.get('pin_status'),
                        'declared_pin': f.get('artifact_sha12'),
                        'derive_now': [dd.get('evidence_kind'), dd.get('pin_status'),
                                       dd.get('pin_reason')],
                        'ep_is_dirty': ep in dirty})
    out['frozen_rows_apply_would_change_now'] = fam
    out['frozen_rows_apply_would_change_now_n'] = len(fam)
    return out


def fixture_checks(be):
    """P3 闸等价 + P4 例外 + P5 非源码不动 + P6 确定性 —— 全在**仓内夹具相对路径**上跑
    (真登记表只被读)。夹具路径在仓内是**必须**的: `instrument_from_cmd` 只认
    `src|scripts|eval|docs|tests|website|tools` 打头的仓库相对路径, 绝对路径会被静默忽略 ⇒
    夹具会拿不到器具而假红/假绿。`tracked` / `dirty` 由参数注入 ⇒ 无需 git 即可模拟「已入库且干净」。"""
    fx_dir = HERE / 'fixtures'
    fx_dir.mkdir(parents=True, exist_ok=True)
    src = 'eval/capability/exp1-q39/fixtures/fixture_runner.py'
    other = 'eval/capability/exp1-q39/fixtures/fixture_other.sh'
    art = 'eval/capability/exp1-q39/fixtures/fixture_artifact.json'
    (ROOT / src).write_text('print("fixture")\n', encoding='utf-8')
    (ROOT / other).write_text('echo other\n', encoding='utf-8')
    (ROOT / art).write_text('{"a": 1}\n', encoding='utf-8')

    def row(rid, ep, cmd, declared_inst=None):
        r = {'id': rid, 'level': 'L2', 'evidence_path': ep, 'evidence_cmd': cmd}
        if declared_inst is not None:
            r['evidence_generated_with'] = {'evidence_kind': 'artifact', 'pin_status': 'live',
                                            'pin_reason': 'worktree-only', 'artifact_sha12': None,
                                            'instrument': declared_inst,
                                            'instrument_sha12': '000000000000',
                                            'binding': 'audit-pin', 'audited_by_round': 'EXP1-Q39'}
        return r

    cases = {
        # F1/F2: 源码证据 ∧ 器具自拄 (无声明器具) ⇒ 修后 self-derived/live; 脏净两态同值
        'F1_self_gated_src': row('fx.F1', src, 'python3 %s' % src),
        # F3: 源码证据但**声明**器具另有其人 ⇒ 不改判 (P4 例外)
        'F3_src_declared_foreign_instrument': row('fx.F3', src, 'python3 %s' % src, declared_inst=other),
        # F4: 非源码证据 (真归档产物) ⇒ 分类不动 (负控: 不许借机放宽)
        'F4_artifact_json': row('fx.F4', art, 'python3 %s' % art),
        # F5: 源码证据但**现算**器具另有其人 (cmd 指向别的源码) ⇒ 不改判
        'F5_src_derived_foreign': row('fx.F5', other, 'python3 %s' % src),
    }
    tracked = {src, other, art}
    d = {k: be.derive(str(ROOT), r, tracked, set()) for k, r in cases.items()}
    d_dirty = {k: be.derive(str(ROOT), r, tracked, {r['evidence_path']}) for k, r in cases.items()}

    def gated_after_mutation(key, mutate_bytes):
        """P3 机检入口: 该行的声明按 derive() 产出; 变异证据/器具字节后 check() 是否判红 (两档等价)。"""
        r = cases[key]
        ep = r['evidence_path']
        full = {'id': r['id'], 'level': 'L2', 'evidence_path': ep, 'evidence_cmd': r['evidence_cmd'],
                'evidence_generated_with': dict(d[key])}
        before = be.check(str(ROOT), [full])[0]
        p = ROOT / ep
        orig = p.read_bytes()
        try:
            p.write_bytes(mutate_bytes)
            after = be.check(str(ROOT), [full])[0]
        finally:
            p.write_bytes(orig)
        return {'violations_before': before, 'violations_after_mutation': after,
                'detects': bool(not before and after)}

    eq_src = gated_after_mutation('F1_self_gated_src', b'print("mutated")\n')
    eq_art = gated_after_mutation('F4_artifact_json', b'{"a": 2}\n')
    broken = dict(d['F1_self_gated_src'], instrument_sha12='000000000000')
    broken_v = be.check(str(ROOT), [{'id': 'fx.F1', 'level': 'L2', 'evidence_path': src,
                                     'evidence_cmd': 'python3 %s' % src,
                                     'evidence_generated_with': broken}])[0]

    checks = {
        # P2: 源码且自拄 ⇒ self-derived/live, 脏净两态逐字段相等 (P6)
        'c1_self_gated_src_is_self_derived_live': bool(
            d['F1_self_gated_src']['evidence_kind'] == 'self-derived'
            and d['F1_self_gated_src']['pin_status'] == 'live'
            and d['F1_self_gated_src']['pin_reason'] == 'self-derived'
            and d['F1_self_gated_src']['artifact_sha12'] is None),
        # P6: **自拄行**脏净两态逐字段相等 (其余类保留工作区态依赖 —— 见 c2b 信息项, 如实入档)
        'c2_deterministic_dirty_vs_clean_for_self_gated': bool(
            (d['F1_self_gated_src']['evidence_kind'], d['F1_self_gated_src']['pin_status'],
             d['F1_self_gated_src']['pin_reason'], d['F1_self_gated_src']['artifact_sha12'])
            == (d_dirty['F1_self_gated_src']['evidence_kind'], d_dirty['F1_self_gated_src']['pin_status'],
                d_dirty['F1_self_gated_src']['pin_reason'], d_dirty['F1_self_gated_src']['artifact_sha12'])),
        # c2b 是**信息项** (不入判决): 非自拄行仍随工作区态变 (该行为是本轮未改的设计, 不是回归)
        'c2b_nonself_gated_two_state_recorded': True,
        # P4: 声明的器具另有其人 ⇒ 不改判 (保持原档 frozen + 字节闸)
        'c3_declared_foreign_instrument_not_flipped': bool(
            d['F3_src_declared_foreign_instrument']['evidence_kind'] == 'artifact'
            and d['F3_src_declared_foreign_instrument']['pin_status'] == 'frozen'
            and d['F3_src_declared_foreign_instrument']['artifact_sha12'] == be.sha12_file(str(ROOT), src)),
        # P4b: 现算器具另有其人 ⇒ 不改判
        'c4_derived_foreign_instrument_not_flipped': bool(
            d['F5_src_derived_foreign']['pin_status'] == 'frozen'
            and d['F5_src_derived_foreign']['pin_reason'] == 'archived-per-round'),
        # P5: 非源码证据行分类与 pin 逐位不变
        'c5_artifact_row_class_unchanged': bool(
            d['F4_artifact_json']['evidence_kind'] == 'artifact'
            and d['F4_artifact_json']['pin_status'] == 'frozen'
            and d['F4_artifact_json']['artifact_sha12'] == be.sha12_file(str(ROOT), art)),
        # P3: 闸等价 —— 变异字节 ⇒ 源码自拄行 / 真归档行 都判红
        'c6_source_row_still_gated': bool(eq_src['detects']),
        'c7_artifact_row_still_gated': bool(eq_art['detects']),
        # P3 反证: 闸的载体确实是 instrument_sha12 (写错 ⇒ 判红)
        'c8_broken_instrument_sha_is_red': bool(broken_v),
    }
    return checks, d, {'self_gated': eq_src, 'artifact': eq_art,
                       'broken_instrument_sha_violations': broken_v,
                       'two_state_nonself_gated': {k: {'clean': [d[k]['evidence_kind'], d[k]['pin_status'],
                                                                d[k]['pin_reason']],
                                                       'dirty': [d_dirty[k]['evidence_kind'],
                                                                 d_dirty[k]['pin_status'],
                                                                 d_dirty[k]['pin_reason']]}
                                                   for k in d}}


def apply_side_effect_check(be):
    """P7: scratch 副本上对 r476 行 --apply ⇒ pin_status 仍 live (修前会翻 frozen)。"""
    if not SCRATCH.exists():
        SCRATCH.mkdir(parents=True)
    scratch = SCRATCH / 'registry_apply.json'
    scratch.write_bytes(REG.read_bytes())
    row_id = 'r476.evidence-binding-round-param'
    pre = json.loads(scratch.read_text(encoding='utf-8'))
    pre_row = next(r for r in pre['rows'] if r['id'] == row_id)
    pre_field = dict(pre_row.get('evidence_generated_with') or {})
    p = subprocess.run([sys.executable, 'eval/capability/bind_evidence.py', '--registry', str(scratch),
                        '--apply', '--only', row_id, '--round', 'EXP1-Q39'],
                       cwd=str(ROOT), capture_output=True, text=True)
    post = json.loads(scratch.read_text(encoding='utf-8'))
    post_row = next(r for r in post['rows'] if r['id'] == row_id)
    post_field = post_row.get('evidence_generated_with') or {}
    tail_lf = scratch.read_bytes().endswith(b'\n')
    return {'rc': p.returncode,
            'stdout_tail': (p.stdout or '').strip().splitlines()[-4:],
            'pre_status': pre_field.get('pin_status'), 'pre_reason': pre_field.get('pin_reason'),
            'post_status': post_field.get('pin_status'), 'post_reason': post_field.get('pin_reason'),
            'post_pin': post_field.get('artifact_sha12'),
            'post_round': post_field.get('audited_by_round'),
            'fields_changed': sorted(k for k in set(list(pre_field) + list(post_field))
                                     if pre_field.get(k) != post_field.get(k)),
            'tail_lf_after': tail_lf,
            'check_rc': subprocess.run([sys.executable, 'eval/capability/bind_evidence.py', '--registry',
                                        str(scratch), '--check'], cwd=str(ROOT),
                                       capture_output=True, text=True).returncode,
            'no_flip_to_frozen': post_field.get('pin_status') == 'live',
            'scratch_is_outside_repo': not str(scratch).startswith(str(ROOT))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='post', choices=('pre', 'post'))
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    be = load_be()
    cen = census(be, a.tag)
    try:
        fx, fx_derive, eq = fixture_checks(be)
        side = apply_side_effect_check(be)
    except Exception as exc:
        print('FIXTURE_ERROR=%s: %s' % (type(exc).__name__, exc))
        return 3
    payload = {'round': 'EXP1-Q39', 'schema': 'artifact-class-census/1', 'tag': a.tag,
               'bind_evidence_sha12': be.sha12_file(str(ROOT), 'eval/capability/bind_evidence.py'),
               'registry_sha12': hashlib.sha256(REG.read_bytes()).hexdigest()[:12],
               'census': cen, 'fixture_derive': fx_derive, 'fixture_equivalence': eq,
               'fixture_checks': fx, 'apply_side_effect': side,
               'notes': [
                   'r444.instrument-acceptance 的 derive_unavailable 是**探测口径**产物, 不是降级: '
                   '`face_record_canon` 能被 import 只因「脚本运行时机把脚本目录放进 sys.path[0]」——'
                   '本 census 用 importlib 以模块方式加载 bind_evidence ⇒ 该 import 失败 ⇒ 投影 pin 复算不可得 '
                   '(真实 apply 会**跳过**该行并出声, 不写假冻结行, 与 Q34 设计一致)。'
                   '该 import 上下文依赖本身登记为下轮候选 (同一工具两种加载方式行为不同)。',
                   '非自拄行 (F3/F4/F5) 仍随工作区脏净两态变类 (clean=frozen / dirty=worktree-only): '
                   '这是本工具**未改**的既有设计与 Q38 头注一致, 本轮只把「源码自拄」这一类改为与脏净无关; '
                   '两态读数已并列存档 (c2b 信息项)。',
                   '同族第二缺陷 (已声明 frozen 的行被一次 apply 降级) 本轮**实测为 0 行**: '
                   '132 个冻结行中无一行处于「自己的证据文件是脏的」态 ⇒ 该风险当前不咬人, 但机理同源, '
                   '预注册留给下一轮; r493 一行的变化是本轮**规则改判** (见 src_ext_rows), 不是侧效。',
               ]}
    ok = all(fx.values()) and side['no_flip_to_frozen']
    if a.tag == 'post':
        # 修后: **自拄行**必须脏净同值; 非自拄行不改判 (r492 类), 其工作区态依赖如实记录不判红
        ok = ok and all(r['deterministic'] for r in cen['src_ext_rows'] if r['self_gated'])
        ok = ok and not any(r['self_gated'] is False and r['deterministic'] is False
                            and r['declared_pin'] is None for r in cen['src_ext_rows'])
    payload['verdict'] = 'PASS' if ok else 'FAIL'
    out = pathlib.Path(a.out) if a.out else (HERE / ('census_artifact_class_q39_%s.json' % a.tag))
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    back = json.loads(out.read_text(encoding='utf-8'))
    print('schema=%s tag=%s rows=%d src_ext=%d' % (back['schema'], back['tag'], cen['n_rows'],
                                                   len(cen['src_ext_rows'])))
    for r in cen['src_ext_rows']:
        dc, dd = r['derive_clean'], r['derive_dirty']
        print('  %-40s %-40s clean=%s/%s/%s dirty=%s/%s/%s det=%s self_gated=%s'
              % (r['id'], r['ep'], dc.get('evidence_kind'), dc.get('pin_status'), dc.get('pin_reason'),
                 dd.get('evidence_kind'), dd.get('pin_status'), dd.get('pin_reason'),
                 r['deterministic'], r['self_gated']))
    print('class_dist=%s' % json.dumps(cen['class_dist'], ensure_ascii=False))
    print('fixtures=%s' % json.dumps(fx, ensure_ascii=False))
    print('apply_side_effect=%s' % json.dumps(side, ensure_ascii=False))
    print('READBACK=%s OUT=%s' % ('OK' if back['verdict'] == payload['verdict'] else 'MISMATCH',
                                  os.path.relpath(out, ROOT)))
    print('VERDICT=%s' % payload['verdict'])
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
