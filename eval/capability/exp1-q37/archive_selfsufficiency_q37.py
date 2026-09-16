#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q37 · 候选②: depth-3 **归档自足**补法 —— 65 个 live 兜底结点转归档 + 显式裁定 + 重跑闭包。

背景 (EXP1-Q36 kpi 边界/产物): Q35 的 depth-3 分类读数 = 155 扫 (archive 90 / **live 兜底 65**)
+ 21 弃权 ⇒ 「归档自足」覆盖 90/177 = 50.8%, 即**只看归档无法复算 depth-3 闭包**。
Q36 记录的补法两条: (a) 把 live 兜底结点转为归档物; (b) 或显式登记「不可归档」理由。本轮两条**同时**做。

预注册 (写于取证前, 本文件即判据载体):
  P1 面定义: 对 Q35 记录里的 155 个**被扫**结点逐一裁定 —— 归档(有副本) / 显式不可归档(闭集理由)。
     分母 = 155 被扫结点 (弃权 21 不在本面, 其理由属 Q35 面, 不得混算)。
  P2 不可归档理由闭集 = {directory_node, gone, unreadable, too_large}; 每件必须落一个理由 (机检)。
  P3 自足判据 (成对, 缺一不可):
     c1 覆盖: 每个被扫结点 ∈ 归档 ∪ 显式理由, 且 Σ == 155;
     c2 **重跑等价**: 用扩展归档(归档优先)重跑 depth-3 抽取, 对**每个已归档结点** n_refs 与 Q35
        现场读数**逐结点相等** (只有等价才叫自足; 归档内容不忠 ⇒ 必须报红);
     c3 归档优先机制可达: 抽掉一个归档副本 ⇒ 该结点必须回落到 live (证明兜底通路非死码)。
  P4 三态判决: 0 全绿 / 2 判据红 / 3 弃权 (源不可读)。发现前提被证伪(如全部不可归档)⇒ 如实写, 不凑绿。
  P5 证据档位: 本文件 + 落盘读数 = L2 (静态/重跑); 归档物逐件 sha256 + 读回 才算 L3 的**归档保真**面。
  P6 判据不放宽: c2 的不等数量 > 0 ⇒ 判红; 不许把「归档不忠」降级成 warning。
"""
import hashlib
import importlib.util
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CAP = os.path.join(ROOT, 'eval', 'capability')
Q34 = os.path.join(CAP, 'exp1-q34')
Q35_REC = os.path.join(CAP, 'exp1-q35', 'depth3_recursion_q35.json')
Q34_SRC = os.path.join(Q34, 'deps_depth2_q34.json')
ARCH = os.path.join(HERE, 'archived_deps_depth3')
OUT = os.path.join(HERE, 'archive_selfsufficiency_q37.json')
CAP_BYTES = 262144
REASONS = ('directory_node', 'gone', 'unreadable', 'too_large')


def q34mod():
    spec = importlib.util.spec_from_file_location('q34_deps', os.path.join(Q34, 'deps_depth2_q34.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def slug(path):
    return path.strip('/').replace('/', '__')


def sha256(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def scan_refs(path, q34):
    """与 Q35 同口径: 目录有界遍历 / 文件直读; 不可读 ⇒ None (弃权)。"""
    if os.path.isdir(path):
        found, n = set(), 0
        for dirpath, _dn, fns in os.walk(path):
            for fn in sorted(fns):
                if n >= q34.MAX_SCAN_FILES:
                    break
                n += 1
                got = q34.refs_in(os.path.join(dirpath, fn))
                if got:
                    found.update(got)
        return found
    got = q34.refs_in(path)
    return None if got is None else set(got)


def base_archive_map():
    """Q34 已入库的 depth-2 归档副本: dep -> 仓内副本路径 (Q35 的 archive 优先面)。"""
    doc = json.load(open(Q34_SRC, encoding='utf-8'))
    m = {}
    for r in doc['depth2']:
        dst = (r.get('archive') or {}).get('dst')
        if not dst:
            continue
        p = dst if os.path.isabs(dst) else os.path.join(ROOT, dst)
        if r['dep'] not in m and os.path.exists(p):
            m[r['dep']] = p
    return m


def dispose(q35):
    """对 155 被扫结点做归档/裁定 (P1/P2)。返回 (arch_map_q37, rows)。"""
    os.makedirs(ARCH, exist_ok=True)
    amap, rows = {}, []
    for dep, info in sorted(q35['per_node'].items()):
        if info['scan_source'] == 'archive':
            rows.append({'node': dep, 'disposition': 'already_archived',
                         'archive_path': info['scan_path'], 'reason': None})
            continue
        p = info['scan_path']
        row = {'node': dep, 'disposition': None, 'archive_path': None, 'reason': None}
        if os.path.isdir(p):
            row.update(disposition='not_archivable', reason='directory_node')
        elif not os.path.exists(p):
            row.update(disposition='not_archivable', reason='gone')
        elif os.path.isfile(p):
            try:
                size = os.path.getsize(p)
                if size > CAP_BYTES:
                    row.update(disposition='not_archivable', reason='too_large')
                else:
                    dst = os.path.join(ARCH, slug(p))
                    shutil.copyfile(p, dst)
                    back = sha256(dst)
                    ok = back == sha256(p) and os.path.getsize(dst) == size
                    assert ok, '归档读回不一致: %s' % p
                    amap[dep] = dst
                    row.update(disposition='archived', archive_path=os.path.relpath(dst, ROOT),
                               bytes=size, sha256=back, source_sha256=back)
            except OSError:
                row.update(disposition='not_archivable', reason='unreadable')
        else:
            row.update(disposition='not_archivable', reason='unreadable')
        rows.append(row)
    return amap, rows


def rerun(q35, q34, extra_map, drop_node=None, corrupt_map=None):
    """归档优先 + 现场兜底的 depth-3 重跑 (与 Q35 同抽取逻辑, 只换扫描面)。

    drop_node: 该结点从**归档面整体**摘除 (Q34 副本 + Q37 新副本) ⇒ 用于验证「回落 live」通路可达。
    corrupt_map: {node: 被污染的副本路径} ⇒ 用于验证 c2 的等价判据有判别力 (不忠的归档必须报红)。
    """
    base = base_archive_map()
    extra = dict(extra_map)
    if drop_node:
        base.pop(drop_node, None)
        extra.pop(drop_node, None)
    corrupt_map = corrupt_map or {}
    per = {}
    for dep, info in sorted(q35['per_node'].items()):
        path, kind = None, None
        cand = base.get(dep) or extra.get(dep)
        if dep in corrupt_map:
            cand = corrupt_map[dep]     # 指向被污染的副本 (负控)
        if cand and os.path.exists(cand):
            path, kind = cand, 'archive'
        elif os.path.exists(dep):
            path, kind = dep, 'live'
        if not path:
            per[dep] = {'scan_source': 'gone_at_audit_time', 'n_refs': None}
            continue
        got = scan_refs(path, q34)
        per[dep] = {'scan_source': kind, 'scan_path': path,
                    'n_refs': (None if got is None else len(got))}
    return per


def compare(per, q35, archived_nodes):
    """c2: 已归档结点 n_refs 与 Q35 现场读数逐结点相等 (只比对两端都取到数的结点)。"""
    diffs = []
    for dep in sorted(archived_nodes):
        old = q35['per_node'][dep]['n_refs']
        new = per[dep]['n_refs']
        if new is None or new != old:
            diffs.append({'node': dep, 'q35_n_refs': old, 'rerun_n_refs': new,
                          'rerun_source': per[dep]['scan_source']})
    return diffs


def selftest():
    q34 = q34mod()
    q35 = json.load(open(Q35_REC, encoding='utf-8'))
    extra, _rows = dispose(q35)
    base = rerun(q35, q34, extra)
    checks = {}
    nodes = sorted(extra)
    checks['c1_have_archived_nodes'] = len(nodes) > 0
    checks['c2_equivalent_on_archive'] = not compare(base, q35, nodes)
    # c3 归档优先机制可达: 把该结点从归档面整体摘除 ⇒ 必须回落到 live (证明兜底通路非死码)
    probe = next((n for n in nodes if os.path.exists(n)), None)
    if probe:
        per2 = rerun(q35, q34, extra, drop_node=probe)
        checks['c3_fallback_to_live'] = (per2[probe]['scan_source'] == 'live')
    else:
        checks['c3_fallback_to_live'] = False
    # c2 的判别力: 污染一个**有引用**的副本 ⇒ 逐结点等价判据必须报红 (否则 c2 是空心判据)
    probe_ref = next((n for n in nodes if q35['per_node'][n]['n_refs'] > 0), None)
    if probe_ref:
        bad = os.path.join(HERE, '_nc_corrupt_probe.bin')
        with open(bad, 'wb') as fh:
            fh.write(b'{"note":"no tmp refs here"}\n')
        per3 = rerun(q35, q34, extra, corrupt_map={probe_ref: bad})
        d3 = compare(per3, q35, [probe_ref])
        checks['c2_detects_corrupt_copy'] = bool(d3)
        os.remove(bad)
    else:
        checks['c2_detects_corrupt_copy'] = False
    print('SELFTEST', checks)
    return 0 if all(checks.values()) else 2


def main():
    if '--selftest' in sys.argv:
        return selftest()
    q34 = q34mod()
    q35 = json.load(open(Q35_REC, encoding='utf-8'))
    extra, rows = dispose(q35)
    archived_nodes = [r['node'] for r in rows if r['disposition'] == 'archived']
    already = [r['node'] for r in rows if r['disposition'] == 'already_archived']
    covered = archived_nodes + already
    per = rerun(q35, q34, extra)
    diffs = compare(per, q35, covered)
    reasons = {}
    for r in rows:
        if r['disposition'] == 'not_archivable':
            reasons[r['reason']] = reasons.get(r['reason'], 0) + 1
    n_scanned = len(q35['per_node'])
    conservation = {
        'c0_rows_eq_scanned': len(rows) == n_scanned,
        'c1a_covered_eq_scanned': len(covered) + sum(reasons.values()) == n_scanned,
        'c1b_reasons_in_closed_set': all(k in REASONS for k in reasons),
        'c1c_every_not_archivable_has_reason': all(r['reason'] in REASONS for r in rows
                                                   if r['disposition'] == 'not_archivable'),
        'c2_rerun_equivalent': not diffs,
    }
    payload = {
        'round': 'EXP1-Q37', 'schema': 'archive-selfsufficiency/1',
        'source': os.path.relpath(Q35_REC, ROOT),
        'prereg': {'P1': '分母 = Q35 的 155 被扫结点 (弃权 21 不混算)',
                   'P2': '不可归档理由闭集 = %s' % list(REASONS),
                   'P3': ['c1 覆盖 == 155', 'c2 重跑逐结点等价', 'c3 归档优先回落可达'],
                   'P4': '0 全绿 / 2 判据红 / 3 弃权'},
        'n_scanned_nodes': n_scanned,
        'already_archived': len(already),
        'newly_archived': len(archived_nodes),
        'not_archivable': sum(reasons.values()),
        'by_reason': reasons,
        'archive_self_sufficient_rate': round(len(covered) / n_scanned, 4) if n_scanned else None,
        'rate_before_Q37': round(len(already) / n_scanned, 4),
        'rerun_source_histogram': {k: sum(1 for v in per.values() if v['scan_source'] == k)
                                   for k in ('archive', 'live', 'gone_at_audit_time')},
        'per_node': per,
        'disposition': rows,
        'rerun_equivalence_diff': diffs,
        'conservation': conservation,
        'note': ('归档 = 逐件 sha256 读回核对 (copied == source); 不可归档 = 闭集理由显式登记; '
                 '「自足」判据 = 归档优先重跑与 Q35 现场读数**逐结点相等** (等价才叫自足)。'),
    }
    ok = all(conservation.values())
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    print('ARCHIVE-SELFSUFFICIENCY scanned=%d already=%d new=%d not_archivable=%s(%s) rate=%.4f(旧 %.4f)'
          % (n_scanned, len(already), len(archived_nodes), sum(reasons.values()), reasons,
             payload['archive_self_sufficient_rate'], payload['rate_before_Q37']))
    print('RERUN sources=%s equivalence_diff=%d' % (payload['rerun_source_histogram'], len(diffs)))
    print('CONSERVATION %s' % conservation)
    print('VERDICT=%s out=%s' % ('PASS' if ok else 'FAIL', OUT))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
