#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""面记录**确定化**层 (EXP1-Q33 · C3) —— 把运行期非语义字段移出被 pin 的字节面。

动因 (Q32 §AG.6.2): `r444.instrument-acceptance` 的冻结 pin 语义是「**提交时点快照**」——
面记录内含 `side_effect_attribution.window.{t0,t1,trace_dir}` (墙钟 + 随机 mkdtemp 目录名),
⇒ **同一命令重跑必然改字节** ⇒ 任何重跑都把冻结 pin 打红 (`bind_evidence --check` 转红, 实证 AG.5.6)。
判定缺陷不是「pin 太严」, 而是**被 pin 的字节面里混进了非语义字段** (skill 铁律: 「逐位相等」判据
必须先声明**非语义字段白名单**)。

本模块 = 唯一实现 (面写出方 `instruments_check.py` 调 `write_record`), 契约:
  · `RUNTIME_FIELDS` —— **声明的**非语义字段清单 (JSON 路径), 值移入侧车 `<record>.runtime.json`;
    记录里原位写哨兵 `<runtime>` ⇒ 记录本身只剩语义内容。
  · 内嵌的同一随机串 (trace_dir 值) 全量替换为哨兵 (防同一随机串散落多处)。
  · 侧车缺/不可解析 ⇒ 调用方判**弃权**(rc=3), 不判绿 (见 instruments_check.py 集成点)。
  · 自检 `--selftest`: ①运行期置换 ⇒ 摘要相同; ②语义扰动 ⇒ 摘要必不同 (非平凡); ③哨兵声明的字段
    必须真实存在于记录 (防「声明了不存在的字段」的空心白名单); ④侧车可回读且含被移出的值。
"""
import hashlib
import json
import os
import sys

SENTINEL = '<runtime>'
# 声明的非语义字段 (JSON 路径); 判据只比较**去掉这些字段后**的字节
RUNTIME_FIELDS = (
    ('side_effect_attribution', 'window', 't0'),
    ('side_effect_attribution', 'window', 't1'),
    ('side_effect_attribution', 'window', 'trace_dir'),
)
RUNTIME_NOTE = ('t0/t1 = 墙钟采样; trace_dir = tempfile.mkdtemp 随机目录 ⇒ 同命令重跑必变, 非语义。'
                '移入侧车后, 记录字节只随**语义内容** (器具结果/读数/守恒式) 变化。')


def sha12(blob):
    if isinstance(blob, str):
        blob = blob.encode('utf-8')
    return hashlib.sha256(blob).hexdigest()[:12]


# ── 语义投影 (C3-b): 由**两次真跑实测差分**得出的运行期字段族 (不是猜的) ──────────────
# 证据: `/tmp/q33_A.json` vs `/tmp/q33_B.json` (同面 `--only probe.grade`, 同树, 相隔 2 s),
# 74 条差异叶子全部落在下表路径族内; 其余 (results/manifest_sha12/conservation/trace 计数…) 逐位相同。
# 模式: scalar = 值换哨兵; array_count = 整族换 {_nonsemantic, n} (保留基数, 去掉邻居/随机内容)。
PROJECTION_RULES = (
    # 运行期墙钟 + 随机目录 (Q32 AG.6.2 的直接动因)
    {'path': 'side_effect_attribution/window/t0', 'mode': 'scalar'},
    {'path': 'side_effect_attribution/window/t1', 'mode': 'scalar'},
    {'path': 'side_effect_attribution/window/trace_dir', 'mode': 'scalar'},
    # 邻居面 (同树其它写者/其它进程在场 ⇒ 快照天生不定)
    {'path': 'side_effect_attribution/census_in_repo_cwd', 'mode': 'array_count'},
    {'path': 'side_effect_attribution/foreign_writes[*]/sha_before', 'mode': 'scalar'},
    {'path': 'side_effect_attribution/foreign_writes[*]/sha_after', 'mode': 'scalar'},
    # 活体/采样类读数
    {'path': 'side_effect_attribution/live_fd_scan/scanned', 'mode': 'scalar'},
    {'path': 'side_effect_attribution/trace/log_bytes', 'mode': 'scalar'},
    {'path': 'side_effect_attribution/trace/raw_paths_sample', 'mode': 'array_count'},
    # 信息项: 记录落在哪 / 侧车落在哪 (同一面在不同路径跑不应改变面身份)
    {'path': 'out', 'mode': 'scalar'},
    {'path': 'canon/runtime_sidecar', 'mode': 'scalar'},
)
NONSEMANTIC_SENTINEL = '<nonsemantic>'


def _walk_paths(doc, spec):
    """按 'a/b[*]/c' 形态返回 [(container, key)] 命中点。"""
    parts = spec.split('/')
    out = []

    def rec(cur, i):
        if i == len(parts):
            return
        key = parts[i]
        if key.endswith('[*]'):
            key = key[:-3]
            if isinstance(cur, dict) and key in cur and isinstance(cur[key], list):
                if i == len(parts) - 1:
                    out.append(cur)
                    return
                for item in cur[key]:
                    rec(item, i + 1)
            return
        if isinstance(cur, dict) and key in cur:
            if i == len(parts) - 1:
                out.append((cur, key))
            else:
                rec(cur[key], i + 1)

    rec(doc, 0)
    return out


def project(doc, strict=True):
    """返回 (proj_doc, report)。strict: 每条规则都必须命中至少一处, 否则抛 KeyError
    (防「声明了不存在的字段」的空心投影 —— 同 RUNTIME_FIELDS 纪律)。"""
    proj = json.loads(json.dumps(doc, ensure_ascii=False))
    report = {'rules': [], 'n_applied': 0}
    for rule in PROJECTION_RULES:
        hits = _walk_paths(proj, rule['path'])
        if not hits:
            if strict:
                raise KeyError('PROJECTION_RULE_UNMATCHED: %s (规则空心 ⇒ 判弃权)' % rule['path'])
            report['rules'].append({'path': rule['path'], 'mode': rule['mode'], 'hits': 0})
            continue
        for h in hits:
            if rule['mode'] == 'scalar':
                container, key = h
                container[key] = NONSEMANTIC_SENTINEL
            else:                                    # array_count
                container, key = h
                val = container[key]
                container[key] = {'_nonsemantic': True,
                                  'n': len(val) if isinstance(val, (list, dict)) else 1}
        report['rules'].append({'path': rule['path'], 'mode': rule['mode'], 'hits': len(hits)})
        report['n_applied'] += len(hits)
    return proj, report


def project_sha12(doc, strict=True):
    proj, report = project(doc, strict=strict)
    return sha12(canonical_bytes(proj)), report


def canonical_bytes(doc):
    return (json.dumps(doc, ensure_ascii=False, indent=1) + '\n').encode('utf-8')


def _get(doc, path):
    cur = doc
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return False, None
        cur = cur[k]
    return True, cur


def _set(doc, path, value):
    cur = doc
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value


def split_runtime(doc, strict=True):
    """返回 (canon_doc, runtime_block)。strict=True 时, 声明字段必须在场 (空心白名单即抛错)。"""
    canon = json.loads(json.dumps(doc, ensure_ascii=False))
    runtime = {'schema': 'face-record-runtime/1', 'note': RUNTIME_NOTE,
               'fields': ['/'.join(p) for p in RUNTIME_FIELDS], 'values': {}}
    trace_dir_val = None
    for path in RUNTIME_FIELDS:
        present, val = _get(canon, path)
        if not present:
            if strict:
                raise KeyError('RUNTIME_FIELD_MISSING: %s (声明的非语义字段不在记录里 ⇒ 白名单空心)'
                               % '/'.join(path))
            continue
        _set(canon, path, SENTINEL)
        runtime['values']['/'.join(path)] = val
        if path[-1] == 'trace_dir':
            trace_dir_val = val
    if trace_dir_val:
        blob = json.dumps(canon, ensure_ascii=False)
        n = blob.count(trace_dir_val)
        if n:
            canon = json.loads(blob.replace(trace_dir_val, SENTINEL))
            runtime['embedded_replacements'] = n
    runtime['canon_sha12'] = sha12(canonical_bytes(canon))
    return canon, runtime


def write_record(doc, target, runtime_target, strict=True):
    """面写出方入口: 记录落 `target` (确定化字节), 运行期字段落 `runtime_target`。"""
    canon, runtime = split_runtime(doc, strict=strict)
    blob = canonical_bytes(canon)
    with open(target, 'wb') as fh:
        fh.write(blob)
    with open(runtime_target, 'wb') as fh:
        fh.write(canonical_bytes(runtime))
    return {'target': str(target), 'runtime_target': str(runtime_target),
            'canon_sha12': sha12(blob), 'canon_bytes': len(blob),
            'runtime_fields': runtime['fields']}


def main():
    args = sys.argv[1:]
    if '--selftest' in args:
        return selftest()
    inp = args[args.index('--in') + 1] if '--in' in args else None
    out = args[args.index('--out') + 1] if '--out' in args else None
    rout = args[args.index('--runtime-out') + 1] if '--runtime-out' in args else None
    if not (inp and out and rout):
        print('usage: face_record_canon.py --in <record.json> --out <canon.json> --runtime-out <rt.json>')
        return 3
    if not os.path.exists(inp):
        print('ENV_FAIL: %s 不存在 ⇒ 弃权' % inp)
        return 3
    doc = json.loads(open(inp, encoding='utf-8').read())
    rep = write_record(doc, out, rout)
    print('CANON %s sha12=%s bytes=%d runtime=%s'
          % (out, rep['canon_sha12'], rep['canon_bytes'], rout))
    return 0


def selftest():
    import tempfile
    tmp = tempfile.mkdtemp(prefix='q33-canon-')
    bad = 0
    cases = {}

    def rec(t0, t1, td, rc0=0, neigh='p1'):
        # 夹具形状与真记录同族 (含邻居面/活体面字段, 否则投影规则会被判空心)
        return {'schema': 'instruments-check/5', 'passed': 1, 'total': 1, 'out': 'eval/x.json',
                'side_effect_attribution': {
                    'window': {'t0': t0, 't1': t1, 'trace_dir': td},
                    'trace': {'commands': 59, 'events': 19, 'log_bytes': 591408,
                              'log_path': td + '/cmd000.log',
                              'raw_paths_sample': ['/tmp/probe_%s/sol.py' % neigh]},
                    'census_in_repo_cwd': [{'pid': 1, 'cmd': 'sleep 10', 'cwd': '.'}],
                    'foreign_writes': [{'path': 'a', 'sha_before': 'x', 'sha_after': 'y'}],
                    'live_fd_scan': {'scanned': 277, 'errors': 105}},
                'canon': {'runtime_sidecar': 'eval/x.runtime.json'},
                'results': [{'id': 'i0', 'rc': rc0, 'pass': rc0 == 0, 'cmd': 'python3 x.py --selftest'}]}
    try:
        a = rec(1789535818.11, 1789536018.22, '/tmp/q22gate-aaaaaa')
        b = rec(1789539999.99, 1789540000.01, '/tmp/q22gate-bbbbbb', neigh='p2')
        ca, ra = split_runtime(a)
        cb, rb = split_runtime(b)
        cases['window_detached_from_record'] = ('/tmp/q22gate-aaaaaa' not in json.dumps(ca)
                                                and SENTINEL in json.dumps(ca))
        # 实测结论 (照原样入档): 仅摘窗口**不足以**让记录字节跨跑相同 —— 邻居面仍在
        cases['record_bytes_still_differ_without_projection'] = (sha12(canonical_bytes(ca))
                                                                 != sha12(canonical_bytes(cb)))
        cases['runtime_values_captured'] = (ra['values']['side_effect_attribution/window/trace_dir']
                                            == '/tmp/q22gate-aaaaaa')
        cases['embedded_random_string_replaced'] = '/tmp/q22gate-aaaaaa' not in json.dumps(ca)
        c = rec(1789535818.11, 1789536018.22, '/tmp/q22gate-aaaaaa', rc0=1)
        cc, _ = split_runtime(c)
        cases['semantic_perturbation_changes_sha12'] = (sha12(canonical_bytes(ca))
                                                        != sha12(canonical_bytes(cc)))
        bad_doc = rec(1789535818.11, 1789536018.22, '/tmp/q22gate-aaaaaa')
        del bad_doc['side_effect_attribution']['window']['t1']
        try:
            split_runtime(bad_doc)
            cases['declared_field_missing_raises'] = False
        except KeyError:
            cases['declared_field_missing_raises'] = True
        # 投影摘要 (C3-b): 对**写出后的记录** (已摘窗口) 计算 —— 运行期/邻居面置换 ⇒ 摘要相同;
        # 语义扰动 ⇒ 必不同; 规则空心 ⇒ 抛错
        pa, ra = project_sha12(ca)
        pb, rb = project_sha12(cb)
        cases['projection_ignores_runtime_and_neighbourhood'] = (pa == pb)
        pc, _ = project_sha12(cc)
        cases['projection_changes_on_semantic_perturbation'] = (pa != pc)
        cases['projection_rules_all_matched'] = all(r['hits'] > 0 for r in ra['rules'])
        try:
            project_sha12({'results': []})
            cases['hollow_projection_rule_rejected'] = False
        except KeyError:
            cases['hollow_projection_rule_rejected'] = True
        # 回读: 侧车 + 记录都能解析, 且记录里不含墙钟值
        p = os.path.join(tmp, 'rec.json')
        rp = os.path.join(tmp, 'rec.runtime.json')
        rep = write_record(a, p, rp)
        cases['write_readback_ok'] = (json.loads(open(p, encoding='utf-8').read())['passed'] == 1
                                      and json.loads(open(rp, encoding='utf-8').read())['schema']
                                      == 'face-record-runtime/1'
                                      and rep['canon_sha12'] == sha12(open(p, 'rb').read()))
        for k, v in cases.items():
            print('  %-40s %s' % (k, 'OK' if v else 'FAIL'))
            bad += 0 if v else 1
        n = len(cases)
        print('SELFTEST %s (%d/%d)' % ('PASS' if bad == 0 else 'FAIL', n - bad, n))
        return 0 if bad == 0 else 2
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
