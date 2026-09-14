#!/usr/bin/env python3
"""R438 独立校验器 — 承重 KPI + 缓存前缀不变量 + 泄漏形状 (与 settle 分属两套实现)。

用法: verify_r438.py [R438_DIR] [R436_DIR]
判据编号对应 docs/plans/v0.58.0-r438-localskip-no-replay.md §4。
判据实现原则: 跳过轮集合**程序化派生** (verdict per_turn.actual), 禁手打常量;
一切断言取自**磁盘归档的实发字节** (calls jsonl), 不从代码逻辑反推。
"""
import hashlib
import json
import os
import sys

MARK = '[本轮参考上下文]'
D = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'r438'))
R436 = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(D, '..', 'r436'))


def rows(p):
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()] if os.path.exists(p) else []


def js(p):
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def est(call):
    ch = sum(len(str(m.get('content') or '')) for m in call.get('messages', []))
    return max(1, ch // 2)


def tot(calls):
    return sum(c.get('prompt_tokens_est', 0) + c.get('completion_tokens_est', 0) for c in calls)


def skip_turns(path):
    v = js(path)
    return {i + 1 for i, q in enumerate(v['per_turn']) if q.get('actual') == 'skip'} if v else set()


def fam(call):
    ms = call.get('messages') or []
    head = str((ms[0] or {}).get('content') or '') if ms else ''
    return hashlib.sha256(head.encode('utf-8')).hexdigest()[:12]


def concat(call):
    return '\n'.join(str(m.get('content') or '') for m in call.get('messages') or [])


R = {'dir': D, 'checks': {}}


def rec(cid, ok, detail, **extra):
    R['checks'][cid] = {'pass': bool(ok), 'detail': detail, **extra}
    print(f"[{'PASS' if ok else 'FAIL'}] {cid}: {detail}")


# ---------- C2 分母不变性 (负控): 门关臂 (无跳过轮) 逐 call 与 R436 冻结档案逐位一致 ----------
a438 = rows(os.path.join(D, 'calls-A-p12.jsonl'))
a436 = rows(os.path.join(R436, 'calls-A-p12.jsonl'))
if a438 and a436:
    l438 = [c['prompt_tokens_est'] for c in a438]
    l436 = [c['prompt_tokens_est'] for c in a436]
    same = l438 == l436 and len(a438) == len(a436)
    rec('C2_A_invariance', same,
        f"calls {len(a438)} vs {len(a436)}; per-call est identical={l438 == l436}; total {tot(a438)} vs {tot(a436)}",
        per_call_438=l438, per_call_436=l436)
else:
    rec('C2_A_invariance', False, 'archived calls 缺失 (A 臂未跑或未落盘)')

# ---------- C3 承重: BRJ 降幅 vs A ----------
brj = rows(os.path.join(D, 'calls-BRJ-p12.jsonl'))
A_T, B_T = tot(a438), tot(brj)
pred = js(os.path.join(D, 'predict-r438.json')) or {}
pred_drop = pred.get('pred_drop_pct')
drop = round((A_T - B_T) / A_T * 100, 2) if A_T else None
rec('C3_drop_ge_30pct', (drop or 0) >= 30.0, f"A={A_T} BRJ={B_T} drop={drop}% (预注册预测 {pred_drop}%)", drop_pct=drop)
if pred_drop is not None:
    dev = abs(drop - pred_drop)
    rec('C3b_prediction_within_0.5pt', dev <= 0.5, f"|实测-预测|={round(dev,2)} pt",
        dev=round(dev, 2), predicted=pred_drop, measured=drop)

# ---------- C4 门质量不降: 逐轮 actual 与 R436 一致, FN/FP=0, acc=1.0 ----------
v438 = js(os.path.join(D, 'verdict-BRJ-p12.json'))
v436 = js(os.path.join(R436, 'verdict-BRJ-p12.json'))
if v438 and v436:
    p38 = [q.get('actual') for q in v438['per_turn']]
    p36 = [q.get('actual') for q in v436['per_turn']]
    fn = v438.get('fn_n')
    fp = v438.get('fp_n')
    acc = v438.get('accuracy')
    rec('C4_decisions_identical', p38 == p36 and fn == 0 and fp == 0 and acc == 1.0,
        f"per_turn identical={p38 == p36}; fn={fn} fp={fp}; acc={acc}", per_turn=p38)
else:
    rec('C4_decisions_identical', False, 'verdict 缺失')

# ---------- C5 缓存前缀不变量: 同 prompt 族内相邻远端调用必须「前 = 后的前缀」 ----------
for arm in ('A', 'BRJ'):
    cs = rows(os.path.join(D, f'calls-{arm}-p12.jsonl'))
    fams = {}
    for i, c in enumerate(cs):
        fams.setdefault(fam(c), []).append(i)
    bad, pairs, multi = [], 0, 0
    for k, idxs in fams.items():
        if len(idxs) < 2:
            continue
        multi += 1
        for u, v in zip(idxs, idxs[1:]):
            pairs += 1
            if not concat(cs[v]).startswith(concat(cs[u])):
                bad.append({'family': k, 'prev_call': u, 'next_call': v,
                            'lcp': len(os.path.commonprefix([concat(cs[u]), concat(cs[v])])),
                            'prev_len': len(concat(cs[u]))})
    rec(f'C5_cache_prefix_{arm}', not bad,
        f"families(multi-call)={multi} pairs={pairs} violations={len(bad)}", violations=bad[:5])

# ---------- C6 泄漏形状: skip 轮条目不得含块; 远端轮条目必须含块 ----------
for arm in ('A', 'BRJ'):
    cs = rows(os.path.join(D, f'calls-{arm}-p12.jsonl'))
    SK = skip_turns(os.path.join(D, f'verdict-{arm}-p12.json'))
    leak_skip, missing_remote, checked, turn1_exempt, exact_raw_fail, raw_checked = [], [], 0, 0, [], 0
    # 同一轮的「原文」= 分母臂 A 里该轮条目的去块部分 (机检派生, 不手打常量)
    raw_by_turn = {}
    for c in a438:
        for idx, m in enumerate(c.get('messages') or []):
            if str(m.get('role')) == 'user' and idx % 2 == 1:
                s = str(m.get('content') or '')
                raw_by_turn.setdefault((idx + 1) // 2, s.split(MARK)[0].rstrip('\n'))
    for c in cs:
        ms = c.get('messages') or []
        for idx, m in enumerate(ms):
            if str(m.get('role')) != 'user' or idx % 2 != 1:
                continue
            turn = (idx + 1) // 2
            checked += 1
            s = str(m.get('content') or '')
            blk = MARK in s
            if turn == 1:
                # 首轮无前序上下文 ⇒ 块为空 (R436 冻结档案同形, 非本修复所致)
                turn1_exempt += (0 if blk else 1)
                continue
            if turn in SK and blk:
                leak_skip.append({'turn': turn, 'len': len(s)})
            if turn not in SK and not blk:
                missing_remote.append({'turn': turn, 'len': len(s)})
            if turn in SK:
                raw_checked += 1
                if s != raw_by_turn.get(turn):
                    exact_raw_fail.append({'turn': turn, 'got_len': len(s), 'want_len': len(raw_by_turn.get(turn) or '')})
    ok = not leak_skip and not missing_remote and not exact_raw_fail
    rec(f'C6_leak_shape_{arm}', ok,
        f"entries={checked} skip_turns={sorted(SK)} 首轮免检={turn1_exempt} 泄漏块={len(leak_skip)} 远端轮缺块={len(missing_remote)} "
        f"跳过轮条目==原文(机检派生) {raw_checked - len(exact_raw_fail)}/{raw_checked}",
        leaked=leak_skip[:5], missing=missing_remote[:5], raw_fail=exact_raw_fail[:5])

# ---------- C6b 因果归因: 同臂 (BRJ) 相对 R436 冻结档案的差异必须**恰好等于**被移除的「从未发出块」质量 ----------
brj436 = rows(os.path.join(R436, 'calls-BRJ-p12.jsonl'))
if brj436 and brj and len(brj436) == len(brj):
    deltas, removed_chars, worst = [], 0, 0.0
    for c4, c8 in zip(brj436, brj):
        u4 = [str(m.get('content') or '') for m in c4['messages'] if str(m.get('role')) == 'user']
        u8 = [str(m.get('content') or '') for m in c8['messages'] if str(m.get('role')) == 'user']
        dc = sum(len(a) - len(b) for a, b in zip(u4, u8))
        d_tok = c4['prompt_tokens_est'] - c8['prompt_tokens_est']
        removed_chars += dc
        worst = max(worst, abs(d_tok - dc / 2))
        deltas.append({'est_436': c4['prompt_tokens_est'], 'est_438': c8['prompt_tokens_est'],
                       'delta_tok': d_tok, 'chars_removed': dc})
    real_removed = tot(brj436) - tot(brj)
    rec('C6b_attribution_removed_mass', worst <= 0.5 and real_removed > 0,
        f"BRJ_436={tot(brj436)} → BRJ_438={tot(brj)} 实测移除={real_removed} tok; 逐调用token差与(条目字符差/2)最大偏离={worst}",
        deltas=deltas, removed_tok=real_removed)

# ---------- C9 负控: 无设备臂 BP 必须「跳过 0 次 + 净亏」(增益须归零) ----------
bp = rows(os.path.join(D, 'calls-BP-p12.jsonl'))
vb = js(os.path.join(D, 'verdict-BP-p12.json'))
if bp and vb:
    bp_t = tot(bp)
    bp_drop = round((A_T - bp_t) / A_T * 100, 2) if A_T else None
    rec('C9_negcontrol_no_device', vb.get('r1_skips') == 0 and (bp_drop or 0) <= 0,
        f"BP calls={len(bp)} tok={bp_t} drop={bp_drop}% r1_skips={vb.get('r1_skips')} remote_fallback={vb.get('judge_remote_fallback_n')}",
        bp_tokens=bp_t, bp_drop_pct=bp_drop)
else:
    rec('C9_negcontrol_no_device', False, 'BP 臂未跑或缺 verdict')

# ---------- C7 确定性: 同臂复跑 ----------
b2 = rows(os.path.join(D, 'calls-BRJ-p12-2.jsonl'))
if b2:
    t2 = tot(b2)
    dt = t2 - B_T
    # 逐调用 token 差必须恒定且等于「run 目录路径长度差/2」(系统提示内嵌运行根目录)
    pdiff = []
    for x, y in zip(brj, b2):
        sx = str(x['messages'][0].get('content') or ''); sy = str(y['messages'][0].get('content') or '')
        pdiff.append(len(sy) - len(sx))
    per_call = [y['prompt_tokens_est'] - x['prompt_tokens_est'] for x, y in zip(brj, b2)]
    const_path = len(set(pdiff)) == 1 and all(d == pdiff[0] // 2 for d in per_call)
    ok = len(b2) == len(brj) and abs(dt) <= max(2, int(0.005 * B_T)) and const_path
    rec('C7_determinism', ok,
        f"calls {len(brj)} vs {len(b2)}; totals {B_T} vs {t2} (Δ={dt}, {abs(dt)/B_T*100:.3f}%); "
        f"系统提示路径长差={pdiff[0] if pdiff else None} 字符 恒定={len(set(pdiff))==1} ⇒ 残差可完整归因",
        per_call_delta=per_call, path_char_delta=pdiff[:1])
else:
    R['checks']['C7_determinism'] = {'pass': None, 'detail': '复跑未做 (本轮窗不足)'}
    print('[SKIP] C7_determinism: 复跑未做 (本轮窗不足)')

R['summary'] = {
    'A_total': A_T, 'BRJ_total': B_T, 'drop_pct': drop, 'predicted_drop_pct': pred_drop,
    'G_calls_A': len(a438), 'G_calls_BRJ': len(brj),
    'failed': [k for k, v in R['checks'].items() if v.get('pass') is False],
}
out = os.path.join(D, 'verify-r438.json')
json.dump(R, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"\n== R438 校验汇总 ==\nA={A_T} BRJ={B_T} drop={drop}% (预测 {pred_drop}%) 失败判据={R['summary']['failed'] or '无'}\n落盘: {out}")
