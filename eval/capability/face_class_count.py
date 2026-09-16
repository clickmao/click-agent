#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q37 · 候选③: 面内「信息项类」成员的计数与判决 (自指成员的真值由**面外**独立轮核验)。

问题: `bind_evidence.{check,committed-state}` 的裁决真值随**树态**翻转 (提交前红/提交后绿),
不能作为面的冻结判据 (Q36 由投影规则 `drop_by_id` 遮蔽, 但面内的 passed/total 仍把它算进分母
⇒ 面读数随提交时点摆动, 且读者无法从面记录区分「真红」与「自指红」)。

设计 (本模块 = 单一事实源, 面与自检共用):
  * 清单行可声明 `class: informational` + `why_informational` (闭集理由); 声明缺失 ⇒ fail-closed。
  * 信息项**照跑照记** (rc/pass 留在 results 里), 只是不进 `passable` 分母 (分母 = 可判据成员)。
  * 判决与计数分离: `passable_failed > 0` ⇒ 面判红 (判据不放宽); 信息项红只单列计数。
  * 三态: 0 全绿 / 1 有真红 / 3 弃权 (由调用方按既有语义决定, 本模块只给计数与 `passable_failed`)。

反向控制 (--selftest, 必须两条都在场, 否则信息项机制会变成遮羞布):
  N1 混合批 (1 信息项红 + 1 普通红) ⇒ `passable_failed == 1` (真红必须仍被计入);
  N2 只信息项红 ⇒ `passable_failed == 0` ∧ `informational_failed == 1` (降级生效且可见);
  N3 声明了信息项但 results 里没有该成员 ⇒ `error` 非空 (fail-closed, 不静默忽略声明);
  N4 无信息项声明 ⇒ 行为与从前逐字段一致 (零回归);
  N5 信息项**通过**时也不得被算进 passable 分母 (分母一致性, 防「通过了才算分母」的错位)。
"""
import json
import sys

REASONS = ('self-referential-tree-state', 'tree-state-dependent-truth')


def partition(results, informational_ids, why_by_id=None):
    """把 results 分成「可判据」与「信息项」两栏 (不改写任何 rc)。"""
    info = set(informational_ids or ())
    why_by_id = why_by_id or {}
    seen = {r['id'] for r in results}
    errs = []
    for i in sorted(info):
        if i not in seen:
            errs.append('informational member absent from results: %s' % i)
        if why_by_id.get(i) not in REASONS:
            errs.append('informational member lacks closed-set reason: %s (%r)'
                        % (i, why_by_id.get(i)))
    passable = [r for r in results if r['id'] not in info]
    inf = [r for r in results if r['id'] in info]
    return {
        'total': len(results),
        'passable_total': len(passable),
        'passable_passed': sum(1 for r in passable if r['pass']),
        'passable_failed': sum(1 for r in passable if not r['pass']),
        'informational_total': len(inf),
        'informational_passed': sum(1 for r in inf if r['pass']),
        'informational_failed': sum(1 for r in inf if not r['pass']),
        'informational_ids': sorted(info),
        'informational_why': {i: why_by_id.get(i) for i in sorted(info)},
        'errors': errs,
    }


def verdict_rc(counts, canon_fail=None, inj_not_applied=False, abstain=False, dirt_penalty=0):
    """三态判决: 3 弃权 / 1 红 (含声明错/面自身脏项) / 0 绿。"""
    if abstain:
        return 3
    if (canon_fail or inj_not_applied or dirt_penalty or counts['errors']
            or counts['passable_failed'] > 0):
        return 1
    return 0


def selftest():
    R = lambda i, ok, cls=None: {'id': i, 'pass': bool(ok)}       # noqa: E731
    N = 'bind_evidence.committed-state'
    why = {N: 'self-referential-tree-state'}
    checks = {}
    # N1 混合: 真红必须仍计入
    c1 = partition([R('a', True), R('b', False), R(N, False)], [N], why)
    checks['N1_real_red_still_counted'] = (c1['passable_failed'] == 1
                                           and c1['informational_failed'] == 1
                                           and verdict_rc(c1) == 1)
    # N2 只信息项红: 降级生效且可见
    c2 = partition([R('a', True), R(N, False)], [N], why)
    checks['N2_info_only_not_red'] = (c2['passable_failed'] == 0
                                      and c2['informational_failed'] == 1
                                      and verdict_rc(c2) == 0)
    # N3 声明缺失 (成员缺席 / 理由不在闭集) ⇒ fail-closed
    c3a = partition([R('a', True)], [N], why)
    c3b = partition([R(N, True)], [N], {N: 'because-i-said-so'})
    checks['N3_missing_member_fail_closed'] = (bool(c3a['errors']) and verdict_rc(c3a) == 1)
    checks['N3_bad_reason_fail_closed'] = (bool(c3b['errors']) and verdict_rc(c3b) == 1)
    # N4 零信息项 ⇒ 计数与旧语义一致
    c4 = partition([R('a', True), R('b', False)], [], {})
    checks['N4_no_info_zero_regression'] = (c4['passable_total'] == 2 and c4['passable_failed'] == 1
                                            and c4['informational_total'] == 0 and verdict_rc(c4) == 1)
    # N5 信息项通过时也不进 passable 分母
    c5 = partition([R('a', True), R(N, True)], [N], why)
    checks['N5_info_pass_excluded_from_denominator'] = (c5['passable_total'] == 1
                                                        and c5['informational_passed'] == 1
                                                        and verdict_rc(c5) == 0)
    # N6 面自身脏项 (罚分) 仍能判红 —— 信息项降级不能连罚分一起吞掉
    checks['N6_dirt_penalty_still_red'] = verdict_rc(c2, dirt_penalty=1) == 1
    print('SELFTEST', json.dumps(checks, ensure_ascii=False))
    return 0 if all(checks.values()) else 2


if __name__ == '__main__':
    sys.exit(selftest())
