#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L2 器具验收面执行器 (R444 · docs/reports/endpoint-and-audit-contract.md L2).

逐条跑 instruments.json: 正控(expect_rc + expect_substr) 与 负控(注入缺陷 ⇒ 必须判红)。
未过 L2 的器具, 其读数不得进台账。产出 eval/capability/instruments-check.json (含器具文件 sha256)。

EXP1-Q19 扩展 (L2 全字段机检, 契约 §L2):
  * `version`            —— 器具版本: 器具内声明值, 或 'content-sha12:<hash>' (由文件字节派生)
  * `version_source`     —— 'declared' | 'content-sha12'  (机检: 与 version 形态一致)
  * `instrument_sha12`   —— 器具文件 sha256[:12]; 机检**重算比对** (漂移 ⇒ 判红)
  * `input_fingerprint`  —— [{path, sha12}] 输入语料指纹; 机检**重算比对** + 路径必须存在
  * `kpi_quad`           —— 口径四元组 (registry schema: 单位/分母/真值源/口径档)
  自检: `--fingerprint-drift-inject` 在内存中篡改首条被选行的指纹期望值 ⇒ 机检必须判红 (rc!=0)。
        这是**机检规范自身**的注入缺陷负控 —— 不配负控的机检是空心的。

EXP1-Q22 扩展 (归因式副作用闸; schema instruments-check/3 → /4):
  * 取代旧判据「`git status` 前后**集合差**」: 每条本面命令经 `strace -f -y` 跟踪写类系统调用,
    窗内脏路径按**写者**归因 —— self_write(判红; 证据=命令序号/pid/系统调用) /
    foreign_write(并发写者, 单列**不判红**, 佐证=持写句柄的外部 pid, 可为空=写者已关句柄) /
    pre_existing(窗内内容未变, 单列不判红); 内容变化且无法归因 ⇒ 判红 (fail-closed)。
    动机: Q21 实测事故 —— 集合差无法区分写者, 对侧在飞的 4 个 tracked 文件被错判成「本面弄脏」,
    本侧据此 `git checkout` 复原, 抹掉对侧未提交改动; 且对已脏路径的重复写入结构性不可见。
  * 输出 `side_effect_attribution` (trace 读数 / live_fd 佐证 / 仓内 cwd 普查 / 守恒式 / 旧闸对比列);
    `side_effects` 语义收窄为「本面命令自己写的路径」(旧值是集合差, 两者不可比)。
  * 跟踪通道不可用 / 被物理上限截断 / 存在不可解析相对名 ⇒ **rc=3 (弃权)**: 既不判绿也不判红。

用法: python3 eval/capability/instruments_check.py [--only id1,id2] [--fingerprint-drift-inject]
"""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'eval/capability/exp1-q22'))
import side_effect_gate as seg  # noqa: E402   (EXP1-Q22 归因式副作用闸)
MAN = ROOT / 'eval/capability/instruments.json'
OUT = ROOT / 'eval/capability/instruments-check.json'
OUT_DRIFT = ROOT / 'eval/capability/instruments-check-drift.json'   # 负控模式独立命名空间 (不得覆盖正控证据)
OUT_SURF_CLAIM = ROOT / 'eval/capability/instruments-check-surface-claim.json'
OUT_SURF_UNKNOWN = ROOT / 'eval/capability/instruments-check-surface-unknown.json'
OUT_NC_NOTAPPLIED = ROOT / 'eval/capability/instruments-check-nc-notapplied.json'
L2_QUAD_KEYS = ('单位', '分母', '真值源', '口径档')
# EXP1-Q21: 输入面语义 (契约 §L2 扩展) —— 空指纹不再默认放行。
SURFACES = ('external_files', 'self_contained', 'dynamic_corpus', 'env_only')
# prior_round_registration = Q19/Q20 轮登记的既往指纹, 未经审计钩子重推导 (显式标为欠账, 不冒充 derived)
SURFACE_SOURCES = ('audit_hook', 'static_literals', 'prior_round_registration')


def sha12(p):
    try:
        return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:12]
    except Exception:
        return None


def run(cmd):
    """跑一条本面命令。EXP1-Q22: 经归因式副作用闸包装 (strace -f 跟踪写类系统调用),
    以便对窗内脏路径按写者归因 —— 见 eval/capability/exp1-q22/side_effect_gate.py。"""
    if GATE is not None:
        return GATE.run(cmd)
    p = subprocess.run(['bash', '-lc', cmd], cwd=str(ROOT), capture_output=True, text=True, timeout=900)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


# 器具自身合法写点 (白名单): 全量面**不得**弄脏既有轮次产物 —— 实测事故: q17 的 `--selftest`
# 默认 `--out` 指向轮次证据 `verdict_q17.json`, 跑一次就把 C12 确定性块抹掉 (证据降级)。
FACE_OUTPUTS = {'eval/capability/instruments-check.json', 'eval/capability/instruments-check-drift.json',
                'eval/capability/instruments-check-surface-claim.json',
                'eval/capability/instruments-check-surface-unknown.json',
                'eval/capability/instruments-check-nc-notapplied.json'}
# EXP1-Q25 增补: r444 可分性预检的**自身产物**是器具的合法写点 (与 q17 事故同族 ——
#   仪器默认 --out 指向轮次证据, 跑一次就改写它)。该器具已按臂分区 (--out 参数化 + 产物带
#   provenance.arm/mode/instrument_sha12), 其内容稳定性由 eval/capability/exp1-q25/harden_check_q25.py
#   的 D1/D2/D3/D7 判据另行钉住 (白名单释放的是"写事件"判定, 不是内容一致性判定)。
FACE_OUTPUTS |= {'eval/rover/r444/precheck-prefilter.json',
                 'eval/rover/r444/runs/precheck-prefilter.neg.json'}
SCRATCH_PREFIXES = ('eval/capability/exp1-q19/l2runs/', 'eval/capability/exp1-q20/l2runs/',
                    'eval/capability/exp1-q21/', 'eval/capability/exp1-q21-selfcheck/')

# EXP1-Q22: 全量面窗口的归因式副作用闸 (None = 未启用, 兼容库调用面)。
GATE = None


def dirt_set():
    p = subprocess.run(['git', 'status', '--porcelain', '--', 'eval', 'docs'],
                       cwd=str(ROOT), capture_output=True, text=True)
    out = set()
    for ln in (p.stdout or '').splitlines():
        parts = ln.strip().split(None, 1)
        if len(parts) == 2:
            out.add(parts[1].strip().strip('"'))
    return out


def check_l2_fields(e):
    """返回 (ok, detail)。机检字段缺失/漂移一律判红, 不放宽。"""
    d = {}
    ver = e.get('version')
    vsrc = e.get('version_source')
    if not isinstance(ver, str) or not ver:
        d['version'] = 'MISSING'
    elif vsrc == 'declared':
        d['version'] = 'declared:' + ver if not ver.startswith('content-sha12:') else 'BAD_FORM'
    elif vsrc == 'content-sha12':
        d['version'] = ('ok' if ver == 'content-sha12:' + (sha12(e.get('evidence_path')) or '')
                        else 'DRIFT')
    else:
        d['version'] = 'BAD_SOURCE'

    want = e.get('instrument_sha12')
    got = sha12(e.get('evidence_path'))
    d['instrument_sha12'] = 'ok' if (want and got and want == got) else f'DRIFT(want={want} got={got})'

    fps = e.get('input_fingerprint')
    surf = e.get('input_surface')
    src = e.get('input_surface_source')
    # EXP1-Q21 语义机检: 「空指纹」不再默认放行 —— 必须显式声明输入面, 且声明与指纹一致。
    if surf not in SURFACES:
        d['input_surface'] = 'BAD/MISSING:%r' % (surf,)
    elif src not in SURFACE_SOURCES:
        d['input_surface_source'] = 'BAD/MISSING:%r' % (src,)
    else:
        d['input_surface'] = 'ok:' + surf
    if not isinstance(fps, list):
        d['input_fingerprint'] = 'MISSING'
    else:
        bad = []
        for it in fps:
            p = (it or {}).get('path') if isinstance(it, dict) else None
            w = (it or {}).get('sha12') if isinstance(it, dict) else None
            if not p:
                bad.append('NOT_DICT_OR_NO_PATH')
                continue
            g = sha12(p)
            if g is None:
                bad.append(f'MISSING_FILE:{p}')
            elif w != g:
                bad.append(f'DRIFT:{p}(want={w} got={g})')
        if surf == 'external_files' and not fps:
            bad.append('EMPTY_FP_FOR_EXTERNAL')
        if surf in ('self_contained', 'dynamic_corpus', 'env_only') and fps:
            bad.append(f'FP_WITHOUT_EXTERNAL_SURFACE(n={len(fps)})')
        if surf == 'dynamic_corpus':
            c = e.get('corpus_dynamic_count')
            if not isinstance(c, int) or c <= 0:
                bad.append('BAD_DYNAMIC_COUNT:%r' % (c,))
        if surf == 'undetermined':
            bad.append('SURFACE_UNDETERMINED')
        if not str(e.get('input_surface_reason') or '').strip():
            bad.append('NO_SURFACE_REASON')
        d['input_fingerprint'] = 'ok(n=%d)' % len(fps) if not bad else ';'.join(bad)

    quad = e.get('kpi_quad')
    d['kpi_quad'] = ('ok' if isinstance(quad, dict) and all(k in quad for k in L2_QUAD_KEYS)
                     else 'MISSING_KEYS')
    return all(v.startswith('ok') or v.startswith('declared:') for v in d.values()), d


DECL_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*VERSION[A-Za-z0-9_]*)\s*=\s*"([^"]+)"', re.M)


def declared_version(path):
    try:
        txt = (ROOT / path).read_text(encoding='utf-8', errors='replace')
    except Exception:
        return None
    m = DECL_RE.search(txt)
    return m.group(2) if m else None


INJECTS = {
    '--fingerprint-drift-inject': ('drift', OUT_DRIFT),
    '--surface-claim-inject': ('surface-claim', OUT_SURF_CLAIM),
    '--surface-unknown-inject': ('surface-unknown', OUT_SURF_UNKNOWN),
    '--surface-missing-inject': ('surface-missing', OUT_NC_NOTAPPLIED),
}


def apply_inject(e, mode):
    """机检自身的注入缺陷负控: 只改**内存中的**字段, 不动文件。返回 (是否施加, 说明)。"""
    if mode == 'drift':
        fps = e.get('input_fingerprint') or []
        if fps and isinstance(fps[0], dict):
            fps[0]['sha12'] = 'deadbeef0000'
            return True, 'fingerprint sha12 → deadbeef0000 (期望 DRIFT)'
        return False, ''
    if mode == 'surface-claim':
        if e.get('input_surface') == 'external_files' and (e.get('input_fingerprint') or []):
            e['input_surface'] = 'self_contained'          # 谎报自包含, 但指纹还在
            return True, 'input_surface → self_contained 而指纹非空 (期望 FP_WITHOUT_EXTERNAL_SURFACE)'
        return False, ''
    if mode == 'surface-unknown':
        e['input_surface'] = 'bogus_surface'
        return True, 'input_surface → bogus_surface (期望 BAD/MISSING)'
    if mode == 'surface-missing':
        e.pop('input_surface', None)
        e.pop('input_surface_source', None)
        return True, 'input_surface 字段移除 (期望 BAD/MISSING —— 旧行未补字段必须判红)'
    return False, ''


def main():
    global GATE
    man = json.loads(MAN.read_text(encoding='utf-8'))
    only = None
    if '--only' in sys.argv:
        only = set(sys.argv[sys.argv.index('--only') + 1].split(','))
    inj_mode, target = None, OUT
    for flag, (mode, path) in INJECTS.items():
        if flag in sys.argv:
            inj_mode, target = mode, path
    drift_inject = inj_mode is not None
    if os.environ.get(seg.GATE_MARKER):
        print('SIDE-EFFECT-GATE: 外层闸标记在场 (嵌套调用) ⇒ 本层不重复挂闸 '
              '(外层 strace 已覆盖本进程树; 实测嵌套 strace 被内核拒绝)')
    else:
        GATE = seg.SideEffectGate(ROOT, face_outputs=FACE_OUTPUTS, scratch=SCRATCH_PREFIXES)
        GATE.begin()
    res, bad, injected, inj_note = [], 0, False, ''
    for e in man['instruments']:
        if only and e['id'] not in only:
            continue
        rc, out = run(e['cmd'])
        ok = (rc == e.get('expect_rc', 0)) and (e.get('expect_substr', '') in out)
        l2_ok, l2 = check_l2_fields(e)
        if inj_mode and not injected:
            applied, note = apply_inject(e, inj_mode)   # 逐行尝试, 首个可施加者生效 (确定性顺序)
            if applied:
                l2_ok, l2 = check_l2_fields(e)
                injected, inj_note = True, note
                l2['INJECTED'] = inj_mode + ': expect-FAIL'
        rec = {'id': e['id'], 'kind': e['kind'], 'cmd': e['cmd'], 'rc': rc, 'expect_rc': e.get('expect_rc', 0),
               'substr_ok': e.get('expect_substr', '') in out, 'pass': bool(ok), 'sha12': sha12(e['evidence_path']),
               'owner_round': e.get('owner_round'), 'kpi_quad': e.get('kpi_quad'),
               'l2_fields': l2, 'l2_ok': bool(l2_ok)}
        ncs = []
        for key, exp in (('nc_cmd', 'nc_expect'), ('nc_cmd2', 'nc_expect2')):
            if not e.get(key):
                continue
            nrc, nout = run(e[key])
            spec = e.get(exp)
            if spec == 'any':
                nok = True
            elif isinstance(spec, str) and spec.startswith('detect:'):
                nok = (nrc == 0) and (spec[7:] in nout)
            else:
                nok = nrc != 0
            ncs.append({'cmd': e[key], 'rc': nrc, 'expect': str(e.get(exp)), 'pass': bool(nok),
                        'head': nout.strip().splitlines()[-1][:160] if nout.strip() else ''})
        rec['negative_controls'] = ncs
        rec['pass'] = bool(rec['pass'] and l2_ok and all(n['pass'] for n in ncs))
        if not rec['pass']:
            bad += 1
        res.append(rec)
        line = (f"{'PASS' if rec['pass'] else 'FAIL'} {e['id']:28s} rc={rc} substr={rec['substr_ok']} "
                f"nc={[n['rc'] for n in ncs]} l2={l2}")
        print(line)
        if not rec['pass']:
            print('   ', out.strip().splitlines()[-3:] if out.strip() else '')
            for n in ncs:
                if not n['pass']:
                    print('    nc FAIL:', n['cmd'], '->', n['head'])
    gate_rep = GATE.end() if GATE is not None else seg.inherited_report()
    self_dirt = [w['path'] for w in gate_rep['self_writes']] + [w['path'] for w in gate_rep['touched_and_gone']]
    if not gate_rep['measurement_ok']:
        print('SIDE-EFFECT-GATE: 测量失败 (%s) ⇒ 弃权 (rc=3, 既不判绿也不判红)' % ','.join(gate_rep['reasons']))
    elif self_dirt:
        bad += 1
        print('SIDE-EFFECT: 本面命令弄脏既有产物 (归因证据完备) ⇒', self_dirt)
    for w in gate_rep['foreign_writes']:
        print('SIDE-EFFECT(foreign ≈ 并发写者, 不判红): %s live_fd=%s' %
              (w['path'], [e['pid'] for e in w.get('live_fd', [])]))
    if gate_rep['pre_existing']:
        print('SIDE-EFFECT(pre-existing, 不判红): %d 条窗内内容未变' % len(gate_rep['pre_existing']))
    if gate_rep['old_gate_false_reds']:
        print('OLD-GATE-FALSE-RED (Q21 事故类): %s' % gate_rep['old_gate_false_reds'])
    for c in gate_rep['census_in_repo_cwd']:
        print('  census(仓内 cwd, 信息项): pid=%s cwd=%s cmd=%s' % (c['pid'], c['cwd'], c['cmd'][:70]))
    doc = {'schema': 'instruments-check/4', 'manifest': 'eval/capability/instruments.json',
           'l2_field_checks': True, 'input_surface_checks': True,
           'drift_injected': bool(inj_mode and injected), 'inject_mode': inj_mode, 'inject_note': inj_note,
           'side_effects': self_dirt,
           'side_effect_attribution': gate_rep,
           'passed': len(res) - bad, 'total': len(res), 'results': res}
    target.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f"\nL2 器具验收面: {len(res) - bad}/{len(res)} 通过; 落盘 {target.relative_to(ROOT)}")
    if inj_mode and not injected:
        print('INJECT-NOT-APPLIED (%s): 无可施加行 ⇒ 负控未施加 (判红)' % inj_mode)
        return 1
    if inj_mode:
        print('INJECT-APPLIED (%s): %s' % (inj_mode, inj_note))
        print('  ⇒ 机检结果: %s' % ('判红 (负控成立)' if bad else '仍全绿 (负控失败!)'))
    elif not gate_rep['measurement_ok']:
        return 3
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
