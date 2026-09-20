#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L3 单一审计面 (R444 契约提案 docs/reports/endpoint-and-audit-contract.md 的 L3 层).

由**权威源派生**, 禁手写:
  - docs/verification-registry.json  → 行数/等级分布/门禁违规(缺 negative_control/covers/owner_round/evidence_path 不存在)
  - eval/capability/kpi.jsonl        → 各轮 KPI 读数 (取每 round 最后一行, 并发追加禁取末行 ⇒ 按 round 归并)
  - eval/capability/baselines.json   → **可观测基准台账** (KPI 的检验数据面; 每条基准 source_path+source_sha12 逐条核对现盘, 漂移即红 ⇒ 改源必重算 pin)
  - docs/plans/*.md                  → 每计划文档的 `状态:` 行
  - eval/rover/r444/verdict-r444-analysis.json (若存在) → L1 验收矩阵 (长度档 × 口径/质量)
输出: docs/reports/status.json  (确定性: 无时间戳, 只有源的 sha256 前 12 位)
用法: python3 eval/capability/status_gen.py [--check] [--registry P] [--baselines P] [--out P]
--check 判绿条件 = 登记表 0 违规 ∧ 基准台账 0 漂移/0 缺源 (派生文件与现盘的逐字节一致性只打印不判绿)
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / 'docs/verification-registry.json'
KPI = ROOT / 'eval/capability/kpi.jsonl'
BASELINES = ROOT / 'eval/capability/baselines.json'
OUT = ROOT / 'docs/reports/status.json'
LV_ORDER = ['L0', 'L1', 'L2', 'L3', 'L4']


def sha12(p):
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    except Exception:
        return None


def registry_view(reg_path=None):
    rp = pathlib.Path(reg_path) if reg_path else REG
    d = json.loads(rp.read_text(encoding='utf-8'))
    rows = d.get('rows', [])
    by_level = {lv: 0 for lv in LV_ORDER}
    violations = []
    warnings = []
    for r in rows:
        lv = str(r.get('level', 'L0'))
        by_level[lv] = by_level.get(lv, 0) + 1
        rid = r.get('id', '?')
        try:
            n = int(lv.lstrip('L'))
        except Exception:
            n = 0
        if n >= 2:
            if not r.get('negative_control'):
                violations.append({'id': rid, 'why': 'L>=2 缺 negative_control'})
            cov = r.get('covers')
            if not cov:
                warnings.append({'id': rid, 'why': 'L>=2 未登记 covers[] (形式规范未强制, 记为告警)'})
            for c in (cov or []):
                if ':' in str(c):
                    violations.append({'id': rid, 'why': f'covers 含冒号(须纯路径): {c}'})
        if not r.get('owner_round'):
            violations.append({'id': rid, 'why': '缺 owner_round'})
        ep = r.get('evidence_path')
        if not ep:
            violations.append({'id': rid, 'why': '缺 evidence_path'})
        elif ';' in str(ep):
            violations.append({'id': rid, 'why': f'evidence_path 分号串联: {ep}'})
        elif not (ROOT / str(ep)).exists() and not str(ep).startswith('/'):
            violations.append({'id': rid, 'why': f'evidence_path 不存在: {ep}'})
    return {'rows': len(rows), 'by_level': by_level, 'violations': violations, 'warnings': warnings,
            'updated_round': d.get('updated_round'), 'sha12': sha12(rp)}


def kpi_view():
    if not KPI.exists():
        return {'lines': 0, 'rounds': [], 'rows_missing_kind': 0, 'non_round_rows': []}
    per = {}
    n = 0
    missing_kind = 0
    non_round = []
    rid_re = re.compile(r'^R\d+$')
    for l in KPI.read_text(encoding='utf-8').splitlines():
        if not l.strip():
            continue
        n += 1
        try:
            r = json.loads(l)
        except Exception:
            continue
        rid = str(r.get('round') or 'unknown')
        if not r.get('kind'):
            missing_kind += 1
        if not rid_re.match(rid):
            non_round.append(rid)
        per[rid] = {'ts': r.get('ts'), 'kind': r.get('kind'), 'grid': r.get('grid'),
                    'bin_sha': str(r.get('bin_sha') or '')[:12], 'readouts': r.get('readouts')}
    rids = [k for k in sorted(per) if rid_re.match(k)]
    return {'lines': n, 'rounds': sorted(per), 'latest': per[rids[-1]] if rids else None,
            'latest_round': rids[-1] if rids else None,
            'rows_missing_kind': missing_kind, 'non_round_rows': sorted(set(non_round)), 'sha12': sha12(KPI)}


def baselines_view(path=None):
    """可观测基准台账视图: 每条基准逐条核对现盘 sha12 (漂移/缺源即入 stale/missing_sources)。"""
    bp = pathlib.Path(path) if path else BASELINES
    if not bp.exists():
        return {'entries': 0, 'by_kind': {}, 'by_face': {}, 'stale': [], 'missing_sources': [],
                'note': f'缺 {bp}'}
    d = json.loads(bp.read_text(encoding='utf-8'))
    entries = d.get('entries') or []
    by_kind, by_face, stale, missing = {}, {}, [], []
    for e in entries:
        k, f = e.get('kind'), e.get('face')
        by_kind[k] = by_kind.get(k, 0) + 1
        by_face[f] = by_face.get(f, 0) + 1
        sp = e.get('source_path')
        p = ROOT / str(sp) if sp else None
        if not p or not p.exists():
            missing.append({'id': e.get('id'), 'source_path': sp})
            continue
        got = sha12(p)
        if got != e.get('source_sha12'):
            stale.append({'id': e.get('id'), 'source_path': sp, 'declared': e.get('source_sha12'), 'disk': got})
    try:
        fname = str(bp.relative_to(ROOT)) if bp.is_absolute() else str(bp)
    except ValueError:
        fname = str(bp)
    return {'schema': d.get('schema'), 'file': fname,
            'file_sha12': sha12(bp), 'entries': len(entries), 'by_kind': by_kind, 'by_face': by_face,
            'stale': stale, 'missing_sources': missing, 'rules': list((d.get('rules') or {}).keys())}


def plans_view():
    out = []
    for p in sorted((ROOT / 'docs/plans').glob('*.md')):
        st = None
        for l in p.read_text(encoding='utf-8', errors='replace').splitlines()[:40]:
            m = re.match(r'^\s*状态\s*[:：]\s*(.+?)\s*$', l)
            if m:
                st = m.group(1)
                break
        out.append({'plan': p.name, 'status': st or 'n/a'})
    return out


def matrix_view():
    p = ROOT / 'eval/rover/r444/verdict-r444-analysis.json'
    if not p.exists():
        return {'note': '未测到 (verdict-r444-analysis.json 缺失)'}
    a = json.loads(p.read_text(encoding='utf-8'))
    cells = []
    for g, d3 in (a.get('D3') or {}).items():
        if not d3:
            continue
        q = (a.get('D7_quality') or {}).get(f'{g}/BRJ') or {}
        cells.append({'grid': g, 'k_over_N': d3['k_over_N'], 'A_remote': d3['A_remote'], 'BRJ_remote': d3['BRJ_remote'],
                      'D_remote_pct': d3['D_remote'], 'D_remote_plus_local_true_pct': d3['D_remote_plus_local_true'],
                      'quality_fn': q.get('fn_n'), 'quality_fp': q.get('fp_n'), 'quality_acc': q.get('accuracy'),
                      'verdict_30pct_api': d3['D_remote'] >= 30.0,
                      'verdict_25pct_with_local': d3['D_remote_plus_local_true'] >= 25.0})
    n1 = a.get('N1N2') or {}
    return {'cells': sorted(cells, key=lambda c: c['grid']),
            'equivalence': {'per_turn_diffs': len(((a.get('D4_equivalence') or {}).get('per_turn_diffs')) or []),
                            'remote_tokens_identical': (a.get('D4_equivalence') or {}).get('remote_tokens_identical'),
                            'gate_r1_calls_BRJ': (a.get('D4_equivalence') or {}).get('gate_r1_calls_BRJ'),
                            'gate_r1_calls_BRJL': (a.get('D4_equivalence') or {}).get('gate_r1_calls_BRJL')},
            'paired_controls': n1,
            'unmeasured': [g for g in ('V2b', 'W8', 'M20') if not (a.get('D3') or {}).get(g)] + ['W20(本轮排除)']}


def _arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def main():
    reg_override = _arg('--registry')
    out_override = _arg('--out')
    bas_override = _arg('--baselines')
    bv = baselines_view(bas_override)
    doc = {'schema': 'status/1', 'derived_from': {'registry': REG.name, 'kpi': 'eval/capability/kpi.jsonl',
                                                  'baselines': 'eval/capability/baselines.json'},
           'registry': registry_view(reg_override), 'kpi': kpi_view(), 'baselines': bv,
           'plans': plans_view(), 'acceptance_matrix': matrix_view(),
           'writer_arbitration': {'policy': 'docs/reports/endpoint-and-audit-contract.md L4',
                                  'hook': 'tools/hooks/pre-commit', 'heartbeat': 'eval/capability/.round_heartbeat'}}
    out = pathlib.Path(out_override) if out_override else OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + '\n'
    rv = doc['registry']
    print(f"registry: {rv['rows']} 行 {rv['by_level']} 违规 {len(rv['violations'])} 告警 {len(rv.get('warnings', []))}")
    for v in rv['violations'][:10]:
        print('  !', v['id'], v['why'])
    kv = doc['kpi']
    print(f"kpi: {kv['lines']} 行, 最新轮 {kv.get('latest_round')} ({kv.get('latest', {}) and (kv['latest'] or {}).get('kind')})"
          f", 缺 kind {kv.get('rows_missing_kind')}, 非轮 tag {kv.get('non_round_rows')}")
    print(f"baselines: {bv['entries']} 条 {bv['by_kind']} | 漂移 {len(bv.get('stale', []))} 缺源 {len(bv.get('missing_sources', []))}"
          f" | 台账 sha12 {bv.get('file_sha12')}")
    for s in bv.get('stale', [])[:5]:
        print('  !', s['id'], s['source_path'], s['declared'], '->', s['disk'])
    for s in bv.get('missing_sources', [])[:5]:
        print('  ! 缺源', s['id'], s['source_path'])
    print(f"plans: {len(doc['plans'])} 份, 进行中 {len([p for p in doc['plans'] if '进行中' in str(p['status'])])}")
    am = doc['acceptance_matrix']
    if 'cells' in am:
        for c in am['cells']:
            print(f"  矩阵 {c['grid']:4s} k/N={c['k_over_N']:6s} 远端 {c['D_remote_pct']:6.2f}% "
                  f"含本地 {c['D_remote_plus_local_true_pct']:6.2f}% 质量 fn={c['quality_fn']} fp={c['quality_fp']}")
        print('  等价性:', am['equivalence'])
        print('  成对控制:', am['paired_controls'])
        print('  未测:', am['unmeasured'])
    else:
        print('  矩阵:', am)
    if '--check' in sys.argv:
        stale, missing = bv.get('stale', []), bv.get('missing_sources', [])
        ok = (not rv['violations']) and (not stale) and (not missing)
        if out.exists():
            cur = out.read_text(encoding='utf-8')
            if cur != txt:
                print('  (派生文件与现盘不一致, 需重跑 status_gen.py; 不判绿)')
        print('CHECK:', 'PASS' if ok else 'FAIL',
              f"(违规 {len(rv['violations'])} / 基准漂移 {len(stale)} / 缺源 {len(missing)})")
        return 0 if ok else 1
    out.write_text(txt, encoding='utf-8')
    print('已落盘:', out, len(txt), 'B')
    return 0


if __name__ == '__main__':
    sys.exit(main())
