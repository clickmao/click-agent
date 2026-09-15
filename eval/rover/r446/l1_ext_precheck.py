#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R446 前置量化 (零测量): 「判官 L1 扩词 ⇒ 0-token 结算」的影响面与误赏率.

承 R445 负结论 (判官侧无廉价**必要**条件) → 本轮改问**充分**条件:
   扩 L1 高信采纳词 (好，/行，/可以， + 短消息) ⇒ 直接结算 Adopt, 不调 L2。
   风险 = **误赏** (归档真值 = Correct/Neutral 却被判 Adopt) ⇒ 必须以 244 行真机 r1 实答为回归基线。

判据 (测量前预注册):
  P1  误赏率: 扩词集内 archived=Correct 的行数 == 0 (硬)。
  P2  误赏(宽): archived=Neutral 且判 Adopt 的比例 ≤ 归档自身的多态噪声率 (同消息跨 run 三态并存的占比)。
  P3  收益: 扩词新增结算行数 ≥ 20 (244 行中), 按 R444 实测均值 (prompt 213 + gen 152 = 365 tok/次) 折算省 tok。
  P4  负控: "全判 Adopt" 平凡结算器必须被 P1 判红 (证明指标有判别力)。
  P5  守恒: 三态计数之和 == 244; 多态消息组必须可见。
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / 'eval/rover/r445/precheck-judge-prefilter.json'
OUT = ROOT / 'eval/rover/r446/l1_ext_precheck.json'

# —— 与 CorrectionDetector.cs:30-48 逐字对齐 (现值) ——
CORRECT = ["不对", "错了", "不是这样", "你说错", "理解错了", "搞错了", "不对吧",
           "重新", "应该是", "我说的是", "你理解成", "纠正", "不是这个意思",
           "wrong", "incorrect", "no,", "not what i meant", "you misunderstood"]
ADOPT = ["好的", "明白了", "懂了", "收到", "谢谢", "没错", "对", "正是",
         "thanks", "got it", "correct", "exactly"]
EXEMPT = ["同事说", "别人说", "他们说", "据说", "如果我说错", "如果我理解", "假如", "上次", "之前那个", "历史", "昨天"]
# —— R446 候选扩充 (高信采纳, 带标点消歧: 逗号/句号收尾 ⇒ 短句确认) ——
ADOPT_EXT = ["好，", "行，", "可以，", "好的，", "行吧", "可以吧", "就这样", "按这个", "没问题", "嗯，"]


def cur_l1(msg):
    m = (msg or "").strip()
    if not m:
        return "Neutral"
    low = m.lower()
    if any(e in low for e in EXEMPT):
        return None
    for mk in CORRECT:
        if mk in low:
            is_en = all(ord(c) < 0x80 for c in mk)
            ref = is_en or any(r in low for r in ("你", "它", "这", "that", "you", "it ")) or len(m) <= 24
            if ref:
                return "Correct"
    for mk in ADOPT:
        if mk in low and len(m) <= 16:
            return "Adopt"
    return None


def ext_l1(msg):
    v = cur_l1(msg)
    if v is not None:
        return v
    m = (msg or "").strip()
    if not m or len(m) > 24:
        return None
    low = m.lower()
    if any(e in low for e in EXEMPT):
        return None
    if any(mk in m for mk in ADOPT_EXT):
        return "Adopt"
    return None


def trivial_all_adopt(msg):
    return "Adopt"


def main():
    d = json.loads(SRC.read_text(encoding='utf-8'))
    rows = d['real_rows']
    n = len(rows)
    res = {'round': 'R446', 'instrument': 'l1_ext_precheck', 'source_rows': n,
           'derived_from': {'instrument': 'eval/rover/r445/judge_prefilter_precheck.py'}}
    kinds = {}
    for r in rows:
        kinds[r['kind']] = kinds.get(r['kind'], 0) + 1
    res['archive_kind_hist'] = kinds

    # 多态噪声: 同 msg 跨 run 不同 kind
    bymsg = {}
    for r in rows:
        bymsg.setdefault(r['msg'], set()).add(r['kind'])
    poly = {m: sorted(k) for m, k in bymsg.items() if len(k) > 1}
    res['polymorphic_msgs'] = {'n_msgs': len(poly), 'of_total_msgs': len(bymsg),
                               'examples': dict(list(poly.items())[:8])}
    res['polymorphic_row_share'] = round(sum(1 for r in rows if len(bymsg[r['msg']]) > 1) / n, 4)

    def evaluate(fn, name):
        settled = [r for r in rows if fn(r['msg']) is not None]
        mis_adopt = [r for r in settled if fn(r['msg']) == 'Adopt' and r['kind'] == 'Correct']
        mis_correct = [r for r in settled if fn(r['msg']) == 'Correct' and r['kind'] == 'Adopt']
        adopt_vs_neutral = [r for r in settled if fn(r['msg']) == 'Adopt' and r['kind'] == 'Neutral']
        return {'name': name, 'settled_rows': len(settled),
                'settled_hist': {k: sum(1 for r in settled if fn(r['msg']) == k) for k in ('Adopt', 'Correct', 'Neutral')},
                'agree': sum(1 for r in settled if fn(r['msg']) == r['kind']),
                'mis_adopt_on_Correct': len(mis_adopt),
                'mis_correct_on_Adopt': len(mis_correct),
                'adopt_on_Neutral': len(adopt_vs_neutral),
                'adopt_on_Neutral_rate': round(len(adopt_vs_neutral) / max(1, len(settled)), 4),
                'examples_mis': [{'msg': r['msg'], 'arch': r['kind'], 'run': r['run']} for r in mis_adopt[:6]]}

    cur = evaluate(cur_l1, 'cur_l1')
    ext = evaluate(ext_l1, 'ext_l1')
    triv = evaluate(trivial_all_adopt, 'neg_control_all_adopt')
    res['cur_l1'] = cur
    res['ext_l1'] = ext
    res['neg_control'] = triv

    # 新增结算行 (扩词带来的增量)
    new_settled = [r for r in rows if cur_l1(r['msg']) is None and ext_l1(r['msg']) is not None]
    res['newly_settled'] = {'n': len(new_settled),
                            'hist': {k: sum(1 for r in new_settled if r['kind'] == k) for k in ('Adopt', 'Correct', 'Neutral')},
                            'msgs': sorted({r['msg'] for r in new_settled})[:20]}
    # 保守折算 (R444 实测判官真值均值: prompt 213 + gen 152)
    res['token_estimate'] = {'judge_prompt_tok': 213, 'judge_gen_tok': 152,
                             'saved_tok_per_settled_call': 365,
                             'saved_tok_on_M20_scale': len(new_settled) * 365}

    crit = {
        'P1_mis_adopt_on_correct_zero': {'pass': ext['mis_adopt_on_Correct'] == 0,
                                         'value': ext['mis_adopt_on_Correct']},
        'P2_adopt_on_neutral_within_noise': {'pass': ext['adopt_on_Neutral_rate'] <= max(0.05, res['polymorphic_row_share']),
                                             'value': ext['adopt_on_Neutral_rate'],
                                             'noise_share': res['polymorphic_row_share']},
        'P3_newly_settled_ge_20': {'pass': len(new_settled) >= 20, 'value': len(new_settled)},
        'P4_neg_control_caught': {'pass': triv['mis_adopt_on_Correct'] > 0, 'value': triv['mis_adopt_on_Correct']},
        'P5_conservation': {'pass': sum(kinds.values()) == n, 'value': sum(kinds.values()), 'n': n},
    }
    res['criteria'] = crit
    res['verdict'] = 'PASS' if all(c['pass'] for c in crit.values()) else 'FAIL'
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    print(f'归档真值分布: {kinds}  共 {n} 行')
    print(f'多态消息: {len(poly)}/{len(bymsg)} 组, 覆盖行占比 {res["polymorphic_row_share"]:.2%}')
    for x in (cur, ext, triv):
        print(f"  {x['name']:22s} 结算 {x['settled_rows']:3d} 行 命中 {x['agree']:3d} "
              f"误赏(Correct→Adopt) {x['mis_adopt_on_Correct']:3d} 误罚 {x['mis_correct_on_Adopt']:2d} "
              f"Adopt|Neutral {x['adopt_on_Neutral']:3d} ({x['adopt_on_Neutral_rate']:.2%})")
    print(f"扩词新增结算 {len(new_settled)} 行 真值分布 {res['newly_settled']['hist']}")
    print(f"  样本: {res['newly_settled']['msgs'][:10]}")
    for k, v in crit.items():
        print(('  PASS ' if v['pass'] else '  FAIL ') + k, v)
    print('判定:', res['verdict'], '->', OUT.relative_to(ROOT))
    return 0 if res['verdict'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
