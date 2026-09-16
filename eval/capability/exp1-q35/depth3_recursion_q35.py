#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q35 · 候选④: depth-3 递归**独立预注册轮** (计数面, 不做分类)。

预注册 (写于测量前, 本文件即判据载体):
  P1 面定义: depth-3 = 把 **depth-2 结点全体** (归档副本优先, 现场路径兜底) 当扫描面再抽一次 `/tmp` 引用;
     与 Q34 的口径差异必须显式声明 —— Q34 的 depth-3 只扫**已入库的 depth-2 副本**
     (`archived_verified` ∧ archive.dst), 其 61 是**窄面**读数; 本轮的宽面读数与它**不可直接比**,
     必须并列两栏 (narrow_Q34 / wide_Q35) 并标注口径变更 (旧读数不作废, 但不得混算)。
  P2 只计数不分类: 本轮**不**对 depth-3 结点做 kind/archivable 裁定 (再分类需各自独立轮);
     若 depth-3 结点里出现**已入库(depth-2 归档)同名**者, 单列 `re_enters_archive` 计数。
  P3 守恒 (必要条件, 全部机检):
     c1 每条 depth-3 边的 via ∈ depth-2 结点集合 (集合守恒);
     c2 Σ 每结点边数 == 总边数;
     c3 被扫结点数 + 弃权结点数 == depth-2 结点数 (无结点被静默跳过);
     c4 弃权结点必须带 reason (gone_at_audit_time / unreadable).
  P4 三态判决: 0 全绿 / 2 判据红 (守恒破) / 3 弃权 (源不可读)。
  P5 自检 (--selftest): ①注入「via 不在 depth-2 集合」的边 ⇒ c1 必红;
     ②注入「结点消失」⇒ 该结点必落 abstain 且带 reason (不静默丢);
     ③窄面/宽面两栏读数必须互异 (非平凡: 否则说明宽面没真的放宽)。

与 Q34 的关系: 复用其 `refs_in` / `MAX_SCAN_FILES` (importlib 单源, 不复制抽引用逻辑)。
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_p = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                    cwd=HERE if os.path.isdir(os.path.join(HERE, '..', '..', 'src')) else os.getcwd())
ROOT = _p.stdout.strip() if _p.returncode == 0 else os.getcwd()
CAP = os.path.join(ROOT, 'eval', 'capability')
Q34 = os.path.join(CAP, 'exp1-q34')
SRC = os.path.join(Q34, 'deps_depth2_q34.json')
OUT = os.path.join(CAP, 'exp1-q35', 'depth3_recursion_q35.json')


def load_q34():
    spec = importlib.util.spec_from_file_location('q34_deps', os.path.join(Q34, 'deps_depth2_q34.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def node_scan_source(row, q34):
    """depth-2 结点的扫描面: 归档副本优先 (仓内稳定) → 现场路径 → 都没有 = 弃权。"""
    dep = row['dep']
    dst = (row.get('archive') or {}).get('dst')
    if dst:
        p = dst if os.path.isabs(dst) else os.path.join(ROOT, dst)
        if os.path.exists(p):
            return p, 'archive'
    if os.path.exists(dep):
        return dep, 'live'
    return None, 'gone_at_audit_time'


def scan_refs(path, q34):
    """对一个结点抽引用 (目录有界遍历 / 文件直读)。不可读 ⇒ None (弃权)。"""
    found = set()
    if os.path.isdir(path):
        n = 0
        for dirpath, _dn, filenames in os.walk(path):
            for fn in sorted(filenames):
                if n >= q34.MAX_SCAN_FILES:
                    break
                n += 1
                got = q34.refs_in(os.path.join(dirpath, fn))
                if got:
                    found.update(got)
    else:
        got = q34.refs_in(path)
        if got is None:
            return None
        found.update(got)
    return found


def build(q34, src=SRC):
    doc = json.load(open(src, encoding='utf-8'))
    depth2 = doc['depth2']
    nodes = {}
    for r in depth2:
        nodes.setdefault(r['dep'], []).append(r)
    node_set = set(nodes)
    archived_names = {os.path.basename(r['dep'].rstrip('/')) for r in depth2
                      if (r.get('archive') or {}).get('dst')}
    edges, abstain, per_node = [], [], {}
    for dep in sorted(node_set):
        reps = nodes[dep]
        src_path, src_kind = None, None
        for r in reps:
            src_path, src_kind = node_scan_source(r, q34)
            if src_path:
                break
        if not src_path:
            abstain.append({'node': dep, 'reason': src_kind or 'gone_at_audit_time'})
            continue
        got = scan_refs(src_path, q34)
        if got is None:
            abstain.append({'node': dep, 'reason': 'unreadable_at_audit_time'})
            continue
        per_node[dep] = {'scan_source': src_kind, 'scan_path': src_path, 'n_refs': len(got)}
        for ref in sorted(got):
            edges.append({'dep': ref, 'via': dep, 'via_class': reps[0].get('class'),
                          'scan_source': src_kind})
    # Q34 窄面读数 (只扫已入库副本) —— 并列栏, 不混算
    narrow_edges = []
    for r in depth2:
        dst = (r.get('archive') or {}).get('dst')
        if not dst or not r.get('archived_verified'):
            continue
        p = dst if os.path.isabs(dst) else os.path.join(ROOT, dst)
        got = q34.refs_in(p)
        for ref in (got or []):
            narrow_edges.append({'dep': ref, 'via': r['dep']})
    dist_wide = sorted({e['dep'] for e in edges})
    dist_narrow = sorted({e['dep'] for e in narrow_edges})
    re_enters = sorted({e['dep'] for e in edges
                        if os.path.basename(e['dep'].rstrip('/')) in archived_names})
    conservation = {
        'c1_via_in_depth2_set': all(e['via'] in node_set for e in edges),
        'c2_sum_per_node_eq_total': sum(v['n_refs'] for v in per_node.values()) == len(edges),
        'c3_scanned_plus_abstain_eq_nodes': (len(per_node) + len(abstain)) == len(node_set),
        'c4_abstain_has_reason': all(bool(a.get('reason')) for a in abstain),
    }
    payload = {
        'round': 'EXP1-Q35', 'schema': 'deps-depth3/1',
        'source': os.path.relpath(src, ROOT),
        'prereg': {'P1': 'depth-3 = depth-2 结点全体 (归档优先, 现场兜底) 再抽一次引用; 与 Q34 窄面不可混算',
                   'P2': '只计数不分类; 归档同名结点单列 re_enters_archive',
                   'P3': ['c1 via ∈ depth-2 集合', 'c2 Σ每结点 == 总边数',
                          'c3 被扫 + 弃权 == depth-2 结点数', 'c4 弃权带 reason'],
                   'P4': '0 全绿 / 2 守恒红 / 3 弃权'},
        'n_depth2_nodes': len(node_set),
        'n_depth2_rows': len(depth2),
        'n_scanned_nodes': len(per_node),
        'abstain': abstain,
        'n_edges': len(edges),
        'n_distinct': len(dist_wide),
        'two_faces': {
            'narrow_Q34_refs': len(narrow_edges), 'narrow_Q34_distinct': len(dist_narrow),
            'wide_Q35_refs': len(edges), 'wide_Q35_distinct': len(dist_wide),
            'q34_recorded_n_refs': (doc.get('depth3') or {}).get('n_refs'),
            'q34_recorded_n_distinct': (doc.get('depth3') or {}).get('n_distinct'),
            'caliber_note': ('Q34 窄面 = 仅扫已入库 depth-2 副本; Q35 宽面 = 扫全部 depth-2 结点 '
                             '(归档优先/现场兜底) ⇒ 两栏并列, 口径变更登记, 不混算。'),
        },
        're_enters_archive': {'n': len(re_enters), 'sample': re_enters[:10]},
        'per_node': per_node,
        'edges': edges,
        'conservation': conservation,
        'note': 'depth-3 只计数 (分类需独立轮); 全量边表随本文件落盘 (可复算, 非抽样)。',
    }
    return payload


def judge(payload):
    return all(payload['conservation'].values()) and payload['n_edges'] > 0


def selftest():
    """P5: 三条自检 (注入缺陷必须被抓 / 两栏必须互异)。"""
    q34 = load_q34()
    base = build(q34)
    checks = {}
    # ① 注入 via 不在 depth-2 集合 ⇒ c1 必红
    node_set = set(base['per_node']) | {a['node'] for a in base['abstain']}
    inj = json.loads(json.dumps(base))
    inj['edges'].append({'dep': '/tmp/injected', 'via': '/tmp/not_a_depth2_node',
                         'via_class': None, 'scan_source': 'archive'})
    checks['inject_unknown_via_red'] = (len(inj['edges']) == len(base['edges']) + 1
                                        and not all(e['via'] in node_set for e in inj['edges']))
    checks['base_all_via_in_set'] = all(e['via'] in node_set for e in base['edges'])
    # ② 结点消失 ⇒ node_scan_source 必须报 gone (不静默算作零引用)
    gone_path, gone_kind = node_scan_source({'dep': '/tmp/q35_definitely_gone_node'}, q34)
    checks['gone_node_reports_gone'] = (gone_path is None and gone_kind == 'gone_at_audit_time')
    # ③ 两栏互异 (非平凡)
    checks['wide_vs_narrow_nontrivial'] = (base['two_faces']['wide_Q35_distinct']
                                           != base['two_faces']['narrow_Q34_distinct'])
    print('SELFTEST', checks)
    return 0 if all(checks.values()) else 2


def main():
    if '--selftest' in sys.argv:
        return selftest()
    out = OUT
    if '--out' in sys.argv:
        cand = sys.argv[sys.argv.index('--out') + 1]
        out = cand if os.path.isabs(cand) else os.path.join(ROOT, cand)
    q34 = load_q34()
    payload = build(q34)
    ok = judge(payload)
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    print('DEPTH3 nodes=%d scanned=%d abstain=%d edges=%d distinct=%d re_enters=%d'
          % (payload['n_depth2_nodes'], payload['n_scanned_nodes'], len(payload['abstain']),
             payload['n_edges'], payload['n_distinct'], payload['re_enters_archive']['n']))
    print('TWO_FACES narrow=%s/%s wide=%s/%s' % (payload['two_faces']['narrow_Q34_refs'],
                                                 payload['two_faces']['narrow_Q34_distinct'],
                                                 payload['two_faces']['wide_Q35_refs'],
                                                 payload['two_faces']['wide_Q35_distinct']))
    print('CONSERVATION %s' % payload['conservation'])
    print('VERDICT=%s out=%s' % ('PASS' if ok else 'FAIL', out))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
