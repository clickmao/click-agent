#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q23 · 6 行 `prior_round_registration` 指纹的审计钩子重推导 (机检口径, 可重算).

机具**单源**: 直接 import EXP1-Q21 的 io_trace (审计钩子) 与 derive_inputs_q21
(run_row / sha12 / sha256sum_cross), 只新增两处:
  1) 排除类 A1: 跟踪器自身产物前缀扩为 .../exp1-q21/ + .../exp1-q23/;
  2) 非语义字段白名单 (generated/elapsed_s) 与「既往登记 vs 派生」关系判定.

判据 P1-P11 见 prereg_q23.json.
用法:
  python3 derive_inputs_q23.py --tag run1 --out eval/capability/exp1-q23/derived_inputs_q23_run1.json
  python3 derive_inputs_q23.py --tag run2 --out .../derived_inputs_q23_run2.json --only <ids>
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
Q21_DIR = ROOT / 'eval' / 'capability' / 'exp1-q21'
TRACE_DIR = HERE / 'l2runs'
NONSEMANTIC = ('generated', 'elapsed_s')          # 预注册白名单: 墙钟/时刻字段只作信息项
SRC = 'prior_round_registration'                  # 本轮清账的目标口径

sys.path.insert(0, str(Q21_DIR))
import io_trace                     # noqa: E402
import derive_inputs_q21 as D       # noqa: E402  (单源: 复用其 run_row/sha12/交叉校验)

D.TRACE_DIR = TRACE_DIR             # 跟踪文件落本轮命名空间 (不改 Q21 已登记的落盘)


def classify_path_q23(p, row):
    """A1: 本轮跟踪器自身产物不进指纹; 其余完全沿用 Q21 的预注册排除规则。"""
    try:
        rel = str(pathlib.Path(p).resolve().relative_to(ROOT))
    except Exception:
        rel = None
    if rel and rel.startswith('eval/capability/exp1-q23/'):
        return 'tracer_self', 'EXP1-Q23 跟踪器自身产物 — 不进指纹 (A1)'
    return D.classify_path(p, row)


def derive_surface(cands, rc, events_n):
    """与 derive_inputs_q21.main 同语义的四分支 (P2)。"""
    if rc not in (0, None) and events_n == 0:
        return 'undetermined', 'rc=%s 且无事件 (测量失败)' % rc
    if not cands:
        return 'self_contained', '无仓库内输入文件 (仅自身/运行时/环境态)'
    if len(cands) > D.CAP_CANDIDATES:
        return 'dynamic_corpus', '仓库内输入面 %d > 上限 %d ⇒ 不冻结' % (len(cands), D.CAP_CANDIDATES)
    return 'external_files', '仓库内输入文件 %d ≤ 上限 %d' % (len(cands), D.CAP_CANDIDATES)


def strip_nonsemantic(obj):
    if isinstance(obj, dict):
        return {k: strip_nonsemantic(v) for k, v in obj.items() if k not in NONSEMANTIC}
    if isinstance(obj, list):
        return [strip_nonsemantic(v) for v in obj]
    return obj


def dirty_set():
    p = subprocess.run(['git', 'status', '--porcelain', '-z', '--untracked-files=all', '--', 'eval', 'docs'],
                       cwd=str(ROOT), capture_output=True, text=True)
    out, i = set(), 0
    f = (p.stdout or '').split('\0')
    while i < len(f):
        if f[i]:
            out.add(f[i][3:])
            if 'R' in f[i][:2] or 'C' in f[i][:2]:
                i += 1
                if i < len(f) and f[i]:
                    out.add(f[i])
        i += 1
    return out


def head_content(rel):
    p = subprocess.run(['git', 'show', 'HEAD:' + rel], cwd=str(ROOT), capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def semantic_equal(rel, before_text, after_text):
    """语义等价: 两版都可解析为 JSON 时去掉非语义字段后比较; 否则按字节判等。"""
    if before_text is None:
        return None, 'no-head'
    try:
        a, b = json.loads(before_text), json.loads(after_text)
    except Exception:
        return before_text == after_text, 'text'
    return strip_nonsemantic(a) == strip_nonsemantic(b), 'json-minus-nonsemantic'


def relation(prior, derived):
    """既往登记 vs 本轮派生: equal / superset / subset / disjoint / mixed + 逐项差异。"""
    pd = {i['path']: i.get('sha12') for i in (prior or []) if isinstance(i, dict) and i.get('path')}
    dd = {i['path']: i.get('sha12') for i in (derived or []) if i.get('path')}
    added = sorted(set(dd) - set(pd))
    removed = sorted(set(pd) - set(dd))
    changed = sorted(p for p in set(pd) & set(dd) if pd[p] != dd[p])
    if not pd and not dd:
        rel = 'both_empty'
    elif added and not removed and not changed:
        rel = 'superset'
    elif removed and not added and not changed:
        rel = 'subset'
    elif not added and not removed and not changed:
        rel = 'equal'
    elif not (set(pd) & set(dd)):
        rel = 'disjoint'
    else:
        rel = 'mixed'
    return {'relation': rel, 'added': added, 'removed': removed, 'sha_changed': changed,
            'prior_n': len(pd), 'derived_n': len(dd)}


def predict_write_targets(cmd):
    """粗筛: 命令里以 eval/ 开头的 .json/.jsonl/.py token (用于事后语义比对)。"""
    return sorted({t for t in cmd.replace('=', ' ').split() if t.startswith('eval/') and t.endswith(('.json', '.jsonl'))})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--timeout', type=int, default=300)
    ap.add_argument('--only', default='')
    ap.add_argument('--crosscheck', action='store_true',
                    help='额外跑一条 Q21 已登记行, 与 Q21 落盘结果逐位比对 (P10)')
    ap.add_argument('--no-restore', action='store_true')
    args = ap.parse_args()

    man = json.loads(REG.read_text(encoding='utf-8'))
    rows = [r for r in man['instruments'] if r.get('input_surface_source') == SRC]
    if args.only:
        want = {x.strip() for x in args.only.split(',') if x.strip()}
        rows = [r for r in rows if r['id'] in want]
    xrow = []
    if args.crosscheck:
        xrow = [r for r in man['instruments']
                if r['id'] in ('r444.prefilter-precheck', 'r444.analyze')]

    before_dirty = dirty_set()
    before_sha = {p: D.sha12(ROOT / p) for p in before_dirty if (ROOT / p).is_file()}
    out = {'ts': time.strftime('%F %T'), 'round': 'EXP1-Q23', 'tag': args.tag,
           'method': 'audit_hook_run (Q21 io_trace 原样) + A1 前缀扩展 + 白名单 %s' % (NONSEMANTIC,),
           'targets_n': len(rows), 'rows': [], 'provider': 'eval/capability/exp1-q21/io_trace.py'}
    hard_fail, traced_writes = [], set()

    for row in rows + xrow:
        got = D.run_row(row, args.timeout)
        rec = {k: got[k] for k in ('id', 'cmd', 'rc', 'elapsed_s', 'stdout_tail', 'sink_n', 'child_n',
                                   'trace_bytes', 'capped', 'malformed_lines',
                                   'tracer_excluded_counters', 'tracer_excluded_examples') if k in got}
        if 'error' in got:
            rec.update({'input_surface': 'undetermined', 'input_surface_reason': got['error']})
            hard_fail.append(got['id'])
            out['rows'].append(rec)
            continue
        reads, writes, scans, spawns = io_trace.classify(got['events'])
        cands, excl = [], {}
        for p in sorted(set(reads) | set(scans)):
            kind, why = classify_path_q23(p, row)
            if kind == 'candidate':
                cands.append(p)
            else:
                excl[kind] = excl.get(kind, 0) + 1
        cands = sorted(set(cands))
        w_in, w_out = [], []
        for p in sorted(set(writes)):
            try:
                rel = str(pathlib.Path(p).resolve().relative_to(ROOT))
            except Exception:
                rel = None
            (w_out if rel is None else w_in).append(rel if rel is not None else p)
        traced_writes |= {p for p in w_in if p}
        fps = []
        for p in cands[:D.CAP_CANDIDATES + 1]:
            try:
                rel = str(pathlib.Path(p).resolve().relative_to(ROOT))
            except Exception:
                rel = p
            fps.append({'path': rel, 'sha12': D.sha12(p), 'sha256sum12': D.sha256sum_cross(p)})
        surf, reason = derive_surface(cands, got['rc'], len(got['events']))
        rec.update({
            'events_n': len(got['events']), 'reads_n': len(reads), 'writes_n': len(writes),
            'scans_n': len(scans), 'spawns_n': len(spawns),
            'input_surface': surf, 'input_surface_source': 'audit_hook', 'input_surface_reason': reason,
            'corpus_dynamic_count': len(cands) if surf == 'dynamic_corpus' else None,
            'excluded_categories': excl,
            'write_paths_in_repo': sorted(set(w_in))[:8], 'write_paths_in_repo_n': len(set(w_in)),
            'write_paths_outside_repo_n': len(w_out),
            'input_fingerprint': [f['path'] for f in fps] if surf == 'external_files' else [],
            'fingerprint_detail': fps if surf == 'external_files' else [],
            'prior_fingerprint': row.get('input_fingerprint') or [],
            'relation_vs_prior': relation(row.get('input_fingerprint'), fps),
            'cmd_write_targets_guess': predict_write_targets(rec.get('cmd') or ''),
            'expect_rc': row.get('expect_rc'), 'expect_substr': row.get('expect_substr'),
            'substr_ok': bool((row.get('expect_substr') or '') in (got.get('stdout_tail') or '')
                              or (row.get('expect_substr') or '') == ''),
            'crosscheck': row['id'] in {r['id'] for r in xrow},
        })
        out['rows'].append(rec)

    # ---- 副作用归属 (P5/P11): 逐路径归因 self/foreign + 语义漂移判定 ----
    after_dirty = dirty_set()
    new_dirt = sorted(after_dirty - before_dirty)
    drift = []
    for rel in new_dirt:
        fp = ROOT / rel
        after_text = fp.read_text(encoding='utf-8', errors='replace') if fp.is_file() else None
        hc = head_content(rel)
        self_written = rel in traced_writes
        if fp.is_file() and rel in before_sha:
            before_text = None
            before_sha_now = D.sha12(fp)
            same_bytes = (before_sha_now == before_sha[rel])
        else:
            same_bytes = False
            before_text = None
        sem, how = (None, 'untracked-new') if hc is None else semantic_equal(rel, hc, after_text or '')
        drift.append({'path': rel, 'self_written_by_this_face': self_written,
                      'attribution': 'self' if self_written else 'foreign',
                      'vs_head_semantic_equal': sem, 'vs_head_method': how,
                      'sha12_in_dirty_snapshot_before': before_sha.get(rel)})
    out['side_effects'] = {
        'scope': ['eval', 'docs'], 'dirty_before_n': len(before_dirty),
        'dirty_after_n': len(after_dirty), 'new_dirty_n': len(new_dirt), 'new_dirty': new_dirt,
        'drift': drift,
        'self_drift_semantic_nonzero': [d['path'] for d in drift
                                        if d['attribution'] == 'self' and d['vs_head_semantic_equal'] is False],
        'pre_existing_untracked': sorted(p for p in before_dirty if not (ROOT / p).is_file() or p not in before_sha)[:12],
    }

    # ---- P10: 与 Q21 落盘结果交叉比对 ----
    xc = []
    q21_out = ROOT / 'eval' / 'capability' / 'exp1-q21' / 'derived_inputs_q21.json'
    if xrow and q21_out.exists():
        old = {r['id']: r for r in json.loads(q21_out.read_text(encoding='utf-8'))['rows']}
        for rec in out['rows']:
            if not rec.get('crosscheck') or rec['id'] not in old:
                continue
            o = old[rec['id']]
            xc.append({'id': rec['id'],
                       'surface_match': o.get('input_surface') == rec.get('input_surface'),
                       'fp_match': (o.get('input_fingerprint') or []) == (rec.get('input_fingerprint') or []),
                       'q21_surface': o.get('input_surface'), 'q23_surface': rec.get('input_surface'),
                       'q21_fp_n': len(o.get('input_fingerprint') or []),
                       'q23_fp_n': len(rec.get('input_fingerprint') or [])})
    out['crosscheck_q21'] = xc

    tgt = [r for r in out['rows'] if not r.get('crosscheck')]
    out['hard_fail'] = hard_fail
    out['summary'] = {
        'rows_n': len(tgt),
        'external_files': sum(1 for r in tgt if r.get('input_surface') == 'external_files'),
        'dynamic_corpus': sum(1 for r in tgt if r.get('input_surface') == 'dynamic_corpus'),
        'self_contained': sum(1 for r in tgt if r.get('input_surface') == 'self_contained'),
        'undetermined': sum(1 for r in tgt if r.get('input_surface') == 'undetermined'),
        'fingerprint_entries': sum(len(r.get('input_fingerprint') or []) for r in tgt),
        'fingerprint_sets_distinct': len({tuple(r.get('input_fingerprint') or []) for r in tgt}),
        'relation_counts': {k: sum(1 for r in tgt if (r.get('relation_vs_prior') or {}).get('relation') == k)
                            for k in ('equal', 'superset', 'subset', 'disjoint', 'mixed', 'both_empty')},
        'sha256sum_cross_mismatch': sum(1 for r in tgt for f in (r.get('fingerprint_detail') or [])
                                        if f['sha256sum12'] not in (None, f['sha12'])),
    }
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    # ---- 复原本面自身造成的「非语义漂移」(P11): 只在前述判定为 self ∧ 语义等价时 ----
    restored = []
    if not args.no_restore:
        todo = [d['path'] for d in drift if d['attribution'] == 'self' and d['vs_head_semantic_equal'] is True]
        if todo:
            p = subprocess.run(['git', 'checkout', '--'] + todo, cwd=str(ROOT), capture_output=True, text=True)
            restored = todo if p.returncode == 0 else ['RESTORE_FAILED:' + p.stderr.strip()[:80]]
    print(json.dumps({'tag': args.tag, 'summary': out['summary'], 'hard_fail': hard_fail,
                      'per_row': {r['id']: [r.get('input_surface'), len(r.get('input_fingerprint') or []),
                                            r.get('events_n'), (r.get('relation_vs_prior') or {}).get('relation')]
                                  for r in tgt},
                      'side_effects': {k: v for k, v in out['side_effects'].items() if k != 'drift'},
                      'crosscheck_q21': xc, 'restored': restored}, ensure_ascii=False, indent=1))
    return 3 if hard_fail else 0


if __name__ == '__main__':
    sys.exit(main())
