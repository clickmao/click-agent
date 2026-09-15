#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q21 · 输入面派生器 (机检口径, 可重算).

把「器具正控命令实际读过哪些输入文件」变成读数: 每行在跟踪器下真跑一次, 采集 open/scandir
事件, 按**预注册排除规则**分类, 产出 input_surface 分类 + 指纹候选 (sha12)。

判据 (P1/P3/P4/P5 见 prereg_q21.json):
- P1: 目标行逐行产出读数, events_n>0 且 rc 为可解释值; 任一行失败 ⇒ 整体 rc=3 (测量失败, 不判红也不判绿)。
- P4: external_files 行的指纹候选非空, 每条 path 存在 ∧ sha12 == hashlib 重算 ∧ 与第三方实现 (sha256sum) 一致。
- P5: self_contained / dynamic_corpus 行**不得**伪造指纹 (空列表 + 显式 reason); dynamic_corpus 记 observed_count。

用法:
  python3 derive_inputs_q21.py --out eval/capability/exp1-q21/derived_inputs_q21.json [--only id1,id2]
"""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REG = ROOT / 'eval' / 'capability' / 'instruments.json'
CAP_CANDIDATES = 24        # 预注册: 超过该数量的输入文件面 ⇒ 判 dynamic_corpus (不冻结)
TRACE_DIR = HERE / 'l2runs'

sys.path.insert(0, str(HERE))
import io_trace  # noqa: E402  (同目录跟踪器, 复用其事件采集与子进程注入)

RUNTIME_PREFIXES = tuple(sorted({
    p for p in (
        sys.prefix, sys.base_prefix,
        os.path.dirname(os.__file__),
    ) if p
})) + ('/usr/lib/python', '/usr/local/lib/python')

# 预注册排除类 ledger_self (见 prereg_q21.json · amendments A1):
# 台账类输入**按设计逐轮变动**, 对它们冻结指纹 = 自指冻结 ⇒ 任何合法登记都会把器具判红。
# 故台账本体不进指纹 (记 reason); 「台账的格式/契约」由各自的形式校验器负责。
LEDGER_SELF = (
    'docs/verification-registry.json',
    'eval/capability/instruments.json',
    'eval/capability/kpi.jsonl',
)


def sha12(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()[:12]


def sha256sum_cross(path):
    """第三方实现交叉: GNU coreutils sha256sum 前 12 位。"""
    try:
        out = subprocess.run(['sha256sum', str(path)], capture_output=True, text=True, timeout=30)
        return out.stdout.split()[0][:12] if out.returncode == 0 and out.stdout else None
    except Exception:
        return None


def classify_path(p, row):
    """预注册排除规则, 顺序即优先级; 返回 ('candidate'|类别, 说明)。"""
    rel = None
    try:
        rel = str(pathlib.Path(p).resolve().relative_to(ROOT))
    except Exception:
        rel = None
    if rel is None:
        return 'outside_repo', '仓库外路径 (临时/系统) — 不进指纹'
    if rel.startswith('.git/'):
        return 'env_state', '版本库内部状态 — 逐轮变化, 不进指纹'
    if '__pycache__' in rel or rel.endswith('.pyc'):
        return 'runtime', '字节码缓存 — 不进指纹'
    if any(p.startswith(pref) for pref in RUNTIME_PREFIXES):
        return 'runtime', '运行时/标准库 — 不进指纹'
    if rel.startswith('eval/capability/exp1-q21/'):
        return 'tracer_self', '跟踪器自身产物 — 不进指纹'
    if rel in LEDGER_SELF:
        return 'ledger_self', '台账本体按设计逐轮变动 (自指冻结) — 不进指纹'
    if row.get('evidence_path') and rel == row['evidence_path']:
        return 'instrument_self', '器具自身 — 已由 instrument_sha12 覆盖'
    ap = ROOT / rel
    if not ap.is_file():
        return 'missing_or_dir', '路径不存在或是目录 — 不进指纹'
    return 'candidate', ''


def run_row(row, timeout):
    rid = row['id']
    live = TRACE_DIR / ('trace_%s.jsonl' % rid.replace('/', '_').replace('.', '-'))
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    if live.exists():
        live.unlink()
    cmd = row.get('cmd') or ''
    if not cmd:
        return {'id': rid, 'rc': None, 'error': 'no cmd'}
    rc, elapsed, out, sink, st = io_trace.run_cmd(cmd, timeout, live)
    io_trace.finalize(st, 'parent')                     # 父进程 summary (计数/上限可见)
    child, child_sums, bad = io_trace.read_trace(live)
    excluded = dict(st['counters'])
    for s in child_sums:
        for k, v in (s.get('excluded_counters') or {}).items():
            excluded[k] = excluded.get(k, 0) + v
    return {'id': rid, 'cmd': cmd, 'rc': rc, 'elapsed_s': round(elapsed, 2),
            'stdout_tail': (out or '').strip()[-300:], 'sink_n': len(sink), 'child_n': len(child),
            'trace_bytes': live.stat().st_size if live.exists() else 0,
            'capped': bool(st['capped'] or any(s.get('capped') for s in child_sums)),
            'malformed_lines': bad, 'tracer_excluded_counters': excluded,
            'tracer_excluded_examples': st['examples'],
            'events': sink + child}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--timeout', type=int, default=300)
    ap.add_argument('--only', default='')
    args = ap.parse_args()

    man = json.loads(REG.read_text(encoding='utf-8'))
    rows = [r for r in man['instruments'] if not r.get('input_fingerprint')]
    if args.only:
        want = {x.strip() for x in args.only.split(',') if x.strip()}
        rows = [r for r in rows if r['id'] in want]
    out = {'ts': time.strftime('%F %T'), 'round': 'EXP1-Q21',
           'method': 'audit_hook_run + 预注册排除规则', 'cap_candidates': CAP_CANDIDATES,
           'targets_n': len(rows), 'rows': [], 'provider': 'eval/capability/exp1-q21/io_trace.py'}

    hard_fail = []
    for row in rows:
        got = run_row(row, args.timeout)
        keys = ('id', 'cmd', 'rc', 'elapsed_s', 'stdout_tail', 'sink_n', 'child_n',
                'trace_bytes', 'capped', 'malformed_lines',
                'tracer_excluded_counters', 'tracer_excluded_examples')
        rec = {k: got[k] for k in keys if k in got}
        if 'error' in got:
            rec['input_surface'] = 'undetermined'
            rec['input_surface_reason'] = got['error']
            hard_fail.append(got['id'])
            out['rows'].append(rec)
            continue
        reads, writes, scans, spawns = io_trace.classify(got['events'])
        cands, excl = [], {}
        for p in sorted(set(reads) | set(scans)):
            kind, why = classify_path(p, row)
            if kind == 'candidate':
                cands.append(p)
            else:
                excl[kind] = excl.get(kind, 0) + 1
        cands = sorted(set(cands))
        w_out, w_other = [], {}
        for p in sorted(set(writes)):
            rel = None
            try:
                rel = str(pathlib.Path(p).resolve().relative_to(ROOT))
            except Exception:
                rel = None
            if rel is None or rel.startswith('/tmp') or p.startswith('/tmp'):
                w_out.append(p)
            else:
                w_other[rel] = w_other.get(rel, 0) + 1

        fps = []
        if cands:
            for p in cands[:CAP_CANDIDATES + 1]:
                try:
                    rel = str(pathlib.Path(p).resolve().relative_to(ROOT))
                except Exception:
                    rel = p
                fps.append({'path': rel, 'sha12': sha12(p), 'sha256sum12': sha256sum_cross(p)})

        if got['rc'] not in (0, None) and len(got['events']) == 0:
            surf, reason = 'undetermined', 'rc=%s 且无事件 (测量失败)' % got['rc']
            hard_fail.append(row['id'])
        elif not cands:
            surf, reason = 'self_contained', '无仓库内输入文件 (仅自身/运行时/环境态)'
        elif len(cands) > CAP_CANDIDATES:
            surf, reason = 'dynamic_corpus', '仓库内输入面 %d > 上限 %d ⇒ 不冻结' % (len(cands), CAP_CANDIDATES)
        else:
            surf, reason = 'external_files', '仓库内输入文件 %d ≤ 上限 %d' % (len(cands), CAP_CANDIDATES)

        rec.update({
            'events_n': len(got['events']), 'reads_n': len(reads), 'writes_n': len(writes),
            'scans_n': len(scans), 'spawns_n': len(spawns),
            'unresolved_relative_n': (got.get('tracer_excluded_counters') or {}).get('unresolved_relative', 0),
            'input_surface': surf, 'input_surface_source': 'audit_hook',
            'input_surface_reason': reason,
            'corpus_dynamic_count': len(cands) if surf == 'dynamic_corpus' else None,
            'excluded_categories': dict(excl, **{k: v for k, v in (got.get('tracer_excluded_counters') or {}).items()}),
            'write_paths_outside_repo': w_out[:8], 'write_paths_in_repo': sorted(w_other)[:8],
            'write_paths_in_repo_n': len(w_other),
            'writes_outside_eval_docs': sorted(p for p in w_other if not (p.startswith('eval/') or p.startswith('docs/')))[:12],
            'input_fingerprint': [f['path'] for f in fps] if surf == 'external_files' else [],
            'fingerprint_detail': fps if surf == 'external_files' else [],
        })
        out['rows'].append(rec)

    out['hard_fail'] = hard_fail
    out['summary'] = {
        'rows_n': len(out['rows']),
        'external_files': sum(1 for r in out['rows'] if r.get('input_surface') == 'external_files'),
        'self_contained': sum(1 for r in out['rows'] if r.get('input_surface') == 'self_contained'),
        'dynamic_corpus': sum(1 for r in out['rows'] if r.get('input_surface') == 'dynamic_corpus'),
        'undetermined': sum(1 for r in out['rows'] if r.get('input_surface') == 'undetermined'),
        'fingerprint_entries': sum(len(r.get('input_fingerprint') or []) for r in out['rows']),
        'cross_check_mismatch': sum(1 for r in out['rows'] for f in (r.get('fingerprint_detail') or [])
                                    if f['sha256sum12'] not in (None, f['sha12'])),
    }
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'summary': out['summary'], 'hard_fail': out['hard_fail'],
                      'per_row': {r['id']: [r.get('input_surface'), len(r.get('input_fingerprint') or []), r.get('events_n')]
                                  for r in out['rows']}}, ensure_ascii=False, indent=1))
    return 3 if hard_fail else 0


if __name__ == '__main__':
    sys.exit(main())
