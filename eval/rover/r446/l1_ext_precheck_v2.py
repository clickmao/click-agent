#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R446 前置量化 v2: 判官侧 0-token 结算 —— **精确串白名单**的最大安全子集搜索.

v1 结论 (已落盘 l1_ext_precheck.json): 「好，/行，/可以，+ contain 匹配」= 不安全
(244 行模糊集内 9 行 Correct→Adopt 误赏, 23 行 Neutral→Adopt) ⇒ 该形态被证伪。

v2 改问: 存在性 —— 是否存在**精确串**(整条消息 == 白名单项)构成的集合 S, 使
   (i) 拟合半上 S 的支撑里 **Correct 计数 == 0** (硬: 不误赏),
   (ii) 留出半上 S 的 **误赏 == 0** 且 **Adopt 精度 ≥ 0.9**,
   (iii) 留出半上**新增结算行数 ≥ 10** (值得实现的收益下界)。
划分: 按 run 名排序后 **奇偶交替** (同消息跨 run 的多态样本因此被拆到两半 ⇒ 留出半是真正的未见样本)。

预注册判据:
  Q1 留出误赏 == 0            (硬)
  Q2 留出 Adopt 精度 ≥ 0.9
  Q3 留出新增结算 ≥ 10 行
  Q4 负控: 把拟合规则放宽为「Correct 计数 > 0 也纳入」⇒ 留出半必须出现误赏 (证明 Q1 有判别力)
  Q5 守恒: 拟合 ∪ 留出 == 244, 且两半不交
"""
import json
import pathlib
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / 'eval/rover/r445/precheck-judge-prefilter.json'
OUT = ROOT / 'eval/rover/r446/l1_ext_precheck_v2.json'


def norm(msg):
    """结算键 = 去空白 + 全角标点归一化(仅用于比对, 不改消息)."""
    s = (msg or '').strip()
    for a, b in (('，', ','), ('。', '.'), ('！', '!'), ('？', '?'), ('、', ','), ('：', ':')):
        s = s.replace(a, b)
    return s


def main():
    rows = json.loads(SRC.read_text(encoding='utf-8'))['real_rows']
    n = len(rows)
    # 奇偶划分 (按 run 排序)
    runs = sorted({r['run'] for r in rows})
    even = {r for i, r in enumerate(runs) if i % 2 == 0}
    fit = [r for r in rows if r['run'] in even]
    hold = [r for r in rows if r['run'] not in even]

    def tab(rs):
        t = defaultdict(Counter)
        for r in rs:
            t[norm(r['msg'])][r['kind']] += 1
        return t

    tf, th = tab(fit), tab(hold)
    # 拟合: 精确串且 Correct==0 且 Adopt>0
    S = {m for m, c in tf.items() if c['Correct'] == 0 and c['Adopt'] > 0 and len(m) <= 24}
    # 负控: 放宽 (允许 Correct>0)
    S_bad = {m for m, c in tf.items() if c['Correct'] > 0 and c['Adopt'] > 0 and len(m) <= 24}

    def ev(S_, rs, include_cur_l1=True):
        settled = [r for r in rs if norm(r['msg']) in S_]
        hist = Counter(r['kind'] for r in settled)
        mis = [r for r in settled if r['kind'] == 'Correct']
        prec = hist['Adopt'] / max(1, len(settled))
        return {'settled': len(settled), 'hist': dict(hist), 'mis_adopt_on_correct': len(mis),
                'adopt_precision': round(prec, 4),
                'examples_mis': [{'msg': r['msg'], 'run': r['run']} for r in mis[:6]]}

    fit_ev = ev(S, fit)
    hold_ev = ev(S, hold)
    bad_ev = ev(S_bad, hold)

    res = {
        'round': 'R446', 'instrument': 'l1_ext_precheck_v2',
        'split': {'runs': len(runs), 'fit_rows': len(fit), 'hold_rows': len(hold),
                  'fit_runs': len(even), 'hold_runs': len(runs) - len(even)},
        'whitelist': {'n': len(S), 'items': sorted(S)},
        'fit_eval': fit_ev, 'hold_eval': hold_ev,
        'neg_control_relaxed': {'n_rules': len(S_bad), 'hold_eval': bad_ev},
        'criteria': {
            'Q1_hold_mis_adopt_zero': {'pass': hold_ev['mis_adopt_on_correct'] == 0, 'value': hold_ev['mis_adopt_on_correct']},
            'Q2_hold_adopt_precision_ge_0.9': {'pass': hold_ev['adopt_precision'] >= 0.9, 'value': hold_ev['adopt_precision']},
            'Q3_hold_settled_ge_10': {'pass': hold_ev['settled'] >= 10, 'value': hold_ev['settled']},
            'Q4_neg_control_caught': {'pass': bad_ev['mis_adopt_on_correct'] > 0, 'value': bad_ev['mis_adopt_on_correct']},
            'Q5_conservation': {'pass': len(fit) + len(hold) == n and not (set(r['run'] for r in fit) & set(r['run'] for r in hold)),
                                'value': len(fit) + len(hold), 'n': n},
        },
    }
    res['verdict'] = 'PASS' if all(c['pass'] for c in res['criteria'].values()) else 'FAIL'
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    print(f"划分: 拟合 {len(fit)} 行/{len(even)} run, 留出 {len(hold)} 行/{len(runs)-len(even)} run")
    print(f"白名单 (正确==0 ∧ Adopt>0, 精确串): {len(S)} 项 -> {sorted(S)}")
    print(f"  拟合: {fit_ev}")
    print(f"  留出: {hold_ev}")
    print(f"  负控(放宽): {bad_ev}")
    for k, v in res['criteria'].items():
        print(('  PASS ' if v['pass'] else '  FAIL ') + k, v)
    print('判定:', res['verdict'], '->', OUT.relative_to(ROOT))
    return 0 if res['verdict'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
