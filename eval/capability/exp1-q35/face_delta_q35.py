#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q35 · 候选①: 定位「逐跑变化语义叶」——面记录逐叶差分 (遮蔽族之外)。

方法: 对每份面记录先用**同一投影规则表**投影 (r454/face_record_canon.project), 再逐叶比较。
     这样差分读数与「pin 到底看见什么」同口径 —— 否则会把已被遮蔽的运行期字段当成差异源。

判据 (预注册 D1a/D1b/D1c):
  D1a 同树态连续跑 (T1..Tn) 的投影后差异叶集合 D_run 必须**逐族可归因**:
      每个差异族的模式必须落在声明的**环境/身份族**内 (pid/live_fd = 进程身份;
      pre_existing/foreign_writes/census = 窗口内环境成员; conservation 计数 = 上述两族的派生)。
      **只要有一个差异叶落在 `/results` (器具行为) 内 ⇒ 判 UNATTRIBUTED** (那才是真·逐跑变化语义叶)。
  D1b 预注册族 (两条): ①`results[*]/sha12` (自写证据重算); ②`side_effect_attribution/*` 环境/身份族。
  D1c 跨树态 (keep1 vs 最新) 差异同样按族报出 (不要求为零, 但必须点名族, 禁"只有一条 committed-state"式的笼统归因)。

退出码: 0 = D_run 全部可归因; 2 = 存在 UNATTRIBUTED (未定位); 3 = 弃权 (记录缺失/不可解析)。
"""
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.dirname(HERE)
sys.path.insert(0, CAP)
import face_record_canon as frc  # noqa: E402

DEFAULT_RECORDS = [
    os.path.join(HERE, 'face_q35_t1.json'),
    os.path.join(HERE, 'face_q35_t2.json'),
    os.path.join(HERE, 'face_q35_t3.json'),
]
BASELINE = os.path.join(CAP, 'exp1-q34', 'face_record_q34_keep1.json')
OUT = os.path.join(HERE, 'face_delta_q35.json')

# 声明的**环境/身份族** (非器具行为): 只这些族允许出现在 D_run 里。
ENV_FAMILIES = (
    'side_effect_attribution/window',
    'side_effect_attribution/trace',
    'side_effect_attribution/census_in_repo_cwd',
    'side_effect_attribution/pre_existing',
    'side_effect_attribution/foreign_writes',
    'side_effect_attribution/live_fd_scan',
    'side_effect_attribution/conservation',
    'side_effect_attribution/self_writes/[*]/evidence/pid',
    'side_effect_attribution/old_gate_delta',
    'side_effect_attribution/old_gate_false_reds',
    'side_effect_attribution/old_gate_missed_self_writes',
    'out',
    'canon/runtime_sidecar',
)
BEHAVIOUR_ROOTS = ('results', 'passed', 'total', 'side_effects', 'side_effect_attribution/verdict',
                   'side_effect_attribution/red', 'side_effect_attribution/measurement_ok',
                   'side_effect_attribution/reasons', 'side_effect_attribution/self_writes')


def walk_leaves(o, prefix=''):
    """叶流: 列表**按下标**取键 (用 [*] 折叠会让同族多项互相覆盖 ⇒ 差异被静默吞掉)。"""
    if isinstance(o, dict):
        for k in o:
            yield from walk_leaves(o[k], prefix + '/' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_leaves(v, prefix + '/' + str(i))
    else:
        yield (prefix, o)


def proj_leaves(doc):
    # strict=False: 真面记录里 foreign_writes/self_writes 等数组**可以为空** (干净窗口) ⇒ 逐规则容忍空心;
    #   锚规则 (window 三件套) 仍 fail-closed (记录不是这一类面 ⇒ 抛错 ⇒ 上游判弃权)。
    proj, _meta = frc.project(doc, strict=False)
    return dict(walk_leaves(proj))


def family(path):
    return re.sub(r'/\d+', '[*]', path)


def in_env_family(path):
    p = path.lstrip('/')
    return any(p == f or p.startswith(f.rstrip('[*]').rstrip('/')) for f in ENV_FAMILIES)


def diff(a, b):
    la, lb = proj_leaves(a), proj_leaves(b)
    keys = sorted(set(la) | set(lb))
    out = []
    for k in keys:
        if la.get(k) != lb.get(k):
            out.append({'leaf': k, 'family': family(k), 'a': repr(la.get(k))[:120],
                        'b': repr(lb.get(k))[:120]})
    return out


def summarize(diffs):
    fam = {}
    for d in diffs:
        f = d['family']
        e = fam.setdefault(f, {'n': 0, 'env_family': in_env_family(d['leaf']), 'sample_a': d['a'],
                               'sample_b': d['b']})
        e['n'] += 1
    unattributed = [d for d in diffs if not in_env_family(d['leaf'])]
    return fam, unattributed


def selftest():
    """防「列表折叠」回归: 同长度列表里仅第 0 项不同 ⇒ 差分**必须**报出 (旧实现会静默吞掉)。"""
    a = {'side_effect_attribution': {'pre_existing': ['x', 'y', 'z']}}
    b = {'side_effect_attribution': {'pre_existing': ['X', 'y', 'z']}}
    d = diff(a, b)
    checks = {'list_head_change_detected': len(d) == 1 and d[0]['leaf'].endswith('/0'),
              'indexed_keys_unique': len(proj_leaves(a)) == 3}
    print('SELFTEST %s' % checks)
    return 0 if all(checks.values()) else 2


def main():
    if '--selftest' in sys.argv:
        return selftest()
    recs = [p for p in sys.argv[1:] if not p.startswith('--')] or DEFAULT_RECORDS
    missing = [p for p in recs + [BASELINE] if not os.path.exists(p)]
    if missing:
        print('ABSTAIN missing records: %s' % missing)
        return 3
    docs = []
    for p in recs:
        with open(p, encoding='utf-8') as fh:
            docs.append((p, json.load(fh)))
    with open(BASELINE, encoding='utf-8') as fh:
        base = json.load(fh)
    payload = {'schema': 'face-delta/1', 'round': 'EXP1-Q35',
               'rules': os.path.relpath(frc.RULES_PATH, os.path.dirname(CAP)),
               'records': [], 'pairs': []}
    for p, d in docs:
        dg, meta = frc.proj_digest(d)
        payload['records'].append({'path': os.path.relpath(p, os.path.dirname(CAP)), 'proj_digest': dg,
                                   'passed': d.get('passed'), 'total': d.get('total'),
                                   'rules_applied': meta['rules_applied'], 'hollow_rules': meta['hollow_rules']})
    payload['records'].append({'path': os.path.relpath(BASELINE, os.path.dirname(CAP)),
                               'proj_digest': frc.proj_digest(base)[0], 'passed': base.get('passed'),
                               'total': base.get('total'), 'baseline': True})
    unattr_total = 0
    # 同树态连续对 (D1a/D1b)
    for i in range(len(docs) - 1):
        diffs = diff(docs[i][1], docs[i + 1][1])
        fam, unattr = summarize(diffs)
        unattr_total += len(unattr)
        payload['pairs'].append({
            'pair': [os.path.basename(docs[i][0]), os.path.basename(docs[i + 1][0])],
            'same_tree_state': True, 'n_differing_leaves': len(diffs),
            'families': {k: {'n': v['n'], 'env_family': v['env_family'],
                             'sample_a': v['sample_a'], 'sample_b': v['sample_b']}
                         for k, v in sorted(fam.items())},
            'digest_a': frc.proj_digest(docs[i][1])[0], 'digest_b': frc.proj_digest(docs[i + 1][1])[0],
            'unattributed': unattr[:20], 'n_unattributed': len(unattr)})
    # 跨树态 (D1c)
    diffs = diff(base, docs[-1][1])
    fam, unattr = summarize(diffs)
    payload['pairs'].append({'pair': ['face_record_q34_keep1.json(envelope)', os.path.basename(docs[-1][0])],
                             'same_tree_state': False, 'n_differing_leaves': len(diffs),
                             'families': {k: {'n': v['n'], 'env_family': v['env_family'],
                                              'sample_a': v['sample_a'], 'sample_b': v['sample_b']}
                                          for k, v in sorted(fam.items())},
                             'n_unattributed': len(unattr), 'unattributed': unattr[:20]})
    # 行为面是否受影响 (关键读数: 器具裁决逐跑稳定?)
    beh = [p for p in payload['pairs'] if p['same_tree_state']]
    payload['behaviour_stable_same_state'] = all(p['n_unattributed'] == 0 for p in beh) if beh else None
    payload['verdict'] = 'ATTRIBUTED' if unattr_total == 0 else 'UNATTRIBUTED'
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    for p in payload['pairs']:
        print('%s vs %s: leaves=%d unattributed=%d'
              % (p['pair'][0], p['pair'][1], p['n_differing_leaves'], p['n_unattributed']))
        for k, v in sorted(p['families'].items(), key=lambda t: -t[1]['n']):
            print('   %-62s n=%-3d env=%s' % (k, v['n'], v['env_family']))
    print('DIGESTS %s' % [(r['path'].split('/')[-1], r['proj_digest']) for r in payload['records']])
    print('VERDICT=%s out=%s' % (payload['verdict'], OUT))
    return 0 if unattr_total == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
