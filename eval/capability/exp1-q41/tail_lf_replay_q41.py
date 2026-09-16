#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q41 · 尾 LF 契约闸的**历史回放**(转正评估) + pin_kind census 负控。

判据不在此处发明 —— `judge()` 直接复用 `eval/capability/exp1-q31/instruments/tail_lf_guard.py`
(单一权威源), 契约名/原因码从 `bind_evidence` 取。

三态退出码: 0 全绿 / 2 判据红 / 3 环境不可判。
墙钟字段只作信息项, 不参与红绿 (R410)。

用法:
  python3 tail_lf_replay_q41.py --json <out.json> [--scope-b-n 200]
"""
import argparse
import collections
import importlib.util
import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # eval/capability/exp1-q41 -> repo root

GUARD = ROOT / 'eval' / 'capability' / 'exp1-q31' / 'instruments' / 'tail_lf_guard.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(*args, binary=True):
    p = subprocess.run(['git'] + list(args), cwd=str(ROOT), capture_output=True)
    if p.returncode != 0:
        return None
    return p.stdout if binary else p.stdout.decode('utf-8', 'replace')


def blob(sha, rel):
    return git('show', '%s:%s' % (sha, rel), binary=True)


def scope_a(tg, json_out):
    """默认作用面: 逐历史提交回放 (提交态字节)。"""
    targets = list(tg.DEFAULT_TARGETS)
    log = git('log', '--format=%H', '--', *targets, binary=False)
    commits = [c for c in (log or '').split() if c]
    rows, viol, missing = [], [], 0
    for sha in commits:
        for rel in targets:
            raw = blob(sha, rel)
            if raw is None:
                missing += 1
                continue
            ok, why = tg.judge(raw)
            rows.append({'sha': sha[:12], 'path': rel, 'ok': bool(ok), 'why': why, 'bytes': len(raw)})
            if not ok:
                viol.append({'sha': sha[:12], 'path': rel, 'why': why})
    out = {'scope': 'A-default-targets', 'targets': targets, 'commits_touching': len(commits),
           'blobs_judged': len(rows), 'missing_path_in_commit': missing,
           'violations': len(viol), 'violation_rows': viol,
           'note': '违规全量归档 (不截断); 截断样本 ⊂ 总体会静默改变判据读数'}
    pathlib.Path(json_out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(json_out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return out


def scope_b(tg, n):
    """扩面代价: 最近 n 个提交的全变更件 (内容法判二进制) —— 用于**否决扩面**。"""
    log = git('log', '--format=%H', '-n', str(n), binary=False)
    commits = [c for c in (log or '').split() if c]
    per_ext = collections.Counter()
    viol = []
    text_n = bin_n = missing = 0
    for sha in commits:
        names = git('show', '--name-only', '--format=', sha, binary=False)
        for rel in [x for x in (names or '').splitlines() if x.strip()]:
            raw = blob(sha, rel)
            if raw is None:
                missing += 1
                continue
            if b'\x00' in raw[:8192]:            # 内容法判二进制 (零后缀白名单)
                bin_n += 1
                continue
            text_n += 1
            ext = pathlib.Path(rel).suffix.lower() or '<none>'
            per_ext[ext] += 1
            ok, why = tg.judge(raw)
            if not ok:
                viol.append({'sha': sha[:12], 'path': rel, 'why': why, 'bytes': len(raw)})
    hit_rate = (len({v['sha'] for v in viol}) / len(commits)) if commits else None
    return {'scope': 'B-broaden-all-text', 'commits_scanned': len(commits),
            'text_blobs_judged': text_n, 'binary_skipped': bin_n, 'missing': missing,
            'violations': len(viol), 'commits_with_violation': len({v['sha'] for v in viol}),
            'commit_hit_rate': hit_rate, 'ext_histogram_top': per_ext.most_common(12),
            'violation_rows': viol}


def judge_fn_control(tg, bi):
    """判据函数判别力成对控制 (防恒真/恒假): 规范形 ⇒ True/None; 破坏形 ⇒ False/NONCANON。"""
    good = b'{"a":1}\n'
    bad_tail = b'{"a":1}'
    bad_bom = b'\xef\xbb\xbf{"a":1}\n'
    bad_crlf = b'{"a":1}\r\n'
    got = {
        'canonical': tg.judge(good),
        'tail_missing': tg.judge(bad_tail),
        'bom': tg.judge(bad_bom),
        'crlf': tg.judge(bad_crlf),
        'empty': tg.judge(b''),
    }
    ok = (got['canonical'] == (True, None) and got['tail_missing'] == (False, bi.NONCANON_REASON)
          and got['bom'][0] is False and got['crlf'][0] is False and got['empty'][0] is False)
    return {'pass': bool(ok), 'readings': {k: list(v) for k, v in got.items()},
            'contract': bi.TAIL_CONTRACT, 'noncanon_reason': bi.NONCANON_REASON}


def pin_kind_census(neg_inject=True):
    """pin_kind 取值集 census + 负控 (注入假取值必须响)。"""
    reg = json.loads((ROOT / 'docs' / 'verification-registry.json').read_text(encoding='utf-8'))
    rows = reg['rows']

    def census(rs):
        c = collections.Counter()
        for r in rs:
            g = r.get('evidence_generated_with')
            c[g.get('pin_kind') if isinstance(g, dict) else '<no-egw>'] += 1
        return dict(c)

    real = census(rows)
    kinds = {k for k in real if k != '<no-egw>'}
    injected = census(rows + [{'evidence_generated_with': {'pin_kind': 'byte-digest-synthetic'}}])
    return {'rows': len(rows), 'census': real,
            'non_default_kinds': sorted(k for k in kinds if k is not None),
            'measurable_objects_for_AN7_3': len([k for k in kinds if k is not None]),
            'negative_control': {'injected_kind_visible': injected.get('byte-digest-synthetic') == 1,
                                 'census_changed': injected != real}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default=str(HERE / 'replay_q41.json'))
    ap.add_argument('--scope-b-n', type=int, default=200)
    a = ap.parse_args()

    if not GUARD.is_file():
        sys.stderr.write('REPLAY: 权威判据件缺失 %s ⇒ rc=3\n' % GUARD)
        return 3
    try:
        tg = load('tail_lf_guard_q41', GUARD)
        bi = load('bind_evidence_q41', ROOT / 'eval' / 'capability' / 'bind_evidence.py')
        judge_control = judge_fn_control(tg, bi)
    except Exception as exc:
        sys.stderr.write('REPLAY: 权威源不可用 (%s) ⇒ rc=3\n' % exc)
        return 3

    t0 = time.perf_counter()
    A = scope_a(tg, str(HERE / 'replay_q41_scopeA.json'))
    B = scope_b(tg, a.scope_b_n)
    budget_ms = (time.perf_counter() - t0) * 1000.0

    # H4 代价: 闸单件 n=5
    costs = []
    for _ in range(5):
        t1 = time.perf_counter()
        subprocess.run(['python3', str(GUARD)], cwd=str(ROOT), capture_output=True)
        costs.append((time.perf_counter() - t1) * 1000.0)
    costs.sort()
    cost = {'n': len(costs), 'min_ms': round(costs[0], 1), 'median_ms': round(costs[len(costs) // 2], 1),
            'max_ms': round(costs[-1], 1), 'note': '墙钟信息项 (同机对侧 dotnet 在飞), 不入判据'}

    pk = pin_kind_census()

    H1 = A['violations'] == 0
    H2_hit = B['commit_hit_rate']
    H2 = (H2_hit is None) or (H2_hit > 0.02)
    H3_guard_ok = judge_control['pass']
    H5 = (pk['non_default_kinds'] == ['semantic-projection']) and pk['negative_control']['census_changed']
    out = {
        'round': 'EXP1-Q41',
        'judge_function_control': judge_control,
        'H1_scopeA_history_zero_false_positive': {'pass': H1, 'reading': A},
        'H2_scopeB_broaden_cost': {'verdict': 'BROADEN_REJECTED' if H2 else 'BROADEN_ALLOWED',
                                   'commit_hit_rate': H2_hit, 'threshold': 0.02, 'reading': B},
        'H4_gate_cost_ms': cost,
        'H5_pin_kind_census': {'pass': H5, 'reading': pk},
        'replay_wall_ms': round(budget_ms, 1),
        'exit_code': 0 if (H1 and H3_guard_ok and H5) else 2,
    }
    pathlib.Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    print('REPLAY contract=%s' % judge_control['contract'])
    print('REPLAY judge_function_control=%s' % ('PASS' if H3_guard_ok else 'FAIL'))
    print('REPLAY H1 scopeA commits=%d blobs=%d violations=%d missing=%d -> %s'
          % (A['commits_touching'], A['blobs_judged'], A['violations'], A['missing_path_in_commit'],
             'PASS' if H1 else 'FAIL'))
    print('REPLAY H2 scopeB commits=%d text_blobs=%d bin_skipped=%d violations=%d hit_rate=%s -> %s'
          % (B['commits_scanned'], B['text_blobs_judged'], B['binary_skipped'], B['violations'],
             ('%.4f' % H2_hit) if H2_hit is not None else 'n/a',
             'BROADEN_REJECTED' if H2 else 'BROADEN_ALLOWED'))
    print('REPLAY H4 gate cost median=%sms min=%sms max=%sms' % (cost['median_ms'], cost['min_ms'], cost['max_ms']))
    print('REPLAY H5 pin_kind census=%s non_default=%s -> %s'
          % (pk['census'], pk['non_default_kinds'], 'PASS' if H5 else 'FAIL'))
    print('REPLAY_EXIT=%d' % out['exit_code'])
    return out['exit_code']


if __name__ == '__main__':
    sys.exit(main())
