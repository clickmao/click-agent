#!/usr/bin/env python3
"""R438 预注册预测器 — 从 R436 归档的 calls 逐字节重放, 用**同一估算器** (字符//2) 预测修复后读数。

修复 (预注册, 未实施): 本地消化轮 (门判 Skip, 无任何远端调用) 的内联块**从未发往任何 provider**
⇒ 不得落进会话历史 (回放字节铁律只约束"真正发出去的"轮次)。当前实现 (IndustrialAgentV2.cs:1267
无条件写 SentContent) 把跳过轮的块写进历史, 被后续每一次远端调用逐字回放。

输出: ① 复现校验 (未剥离时应逐 call 复现归档 prompt_tokens_est) ② 剥离后的预测读数。
"""
import json, os, sys

D = os.path.abspath(os.path.dirname(__file__))
R436 = os.path.join(D, '..', 'r436')
MARK = '[本轮参考上下文]'
SKIP_TURNS_FROM = 'verdict-{arm}-p12.json'   # 跳过轮**程序化派生** (禁手打常量): 取归档 per_turn.actual=='skip'

def est(msgs):
    chars = sum(len(m['content']) for m in msgs if isinstance(m.get('content'), str))
    return max(1, chars // 2)

def strip_block(content):
    i = content.find('\n\n' + MARK)
    return content[:i] if i >= 0 else content

def load(p):
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]

def total_of(calls):
    return sum(c.get('prompt_tokens_est', 0) + c.get('completion_tokens_est', 0) for c in calls)

out = {'arms': {}}
for arm in ('A', 'BRJ'):
    v = json.load(open(os.path.join(R436, SKIP_TURNS_FROM.format(arm=arm)), encoding='utf-8'))
    SKIP_TURNS = {i + 1 for i, q in enumerate(v['per_turn']) if q['actual'] == 'skip'}
    out.setdefault('skip_turns_by_arm', {})[arm] = sorted(SKIP_TURNS)
    calls = load(os.path.join(R436, f'calls-{arm}-p12.jsonl'))
    rec, sim_new, rows = [], [], []
    for k, c in enumerate(calls, 1):
        msgs = [dict(m) for m in c['messages']]
        rec.append(est(msgs))
        for m in msgs:
            if m['role'] != 'user':
                continue
            turn = None
            rows_present = True
        # 逐条 user 消息定位轮号: 索引 i (1-based) → 轮 (i+1)/2
        for idx, m in enumerate(c['messages']):
            if m['role'] == 'user' and idx % 2 == 1:
                turn = (idx + 1) // 2
                if turn in SKIP_TURNS:
                    msgs[idx] = {**m, 'content': strip_block(m['content'])}
        sim_new.append(est(msgs))
        rows.append({'call': k, 'nmsg': len(c['messages']), 'archived': c['prompt_tokens_est'],
                     'repro_from_chars': rec[-1], 'pred_after_fix': sim_new[-1],
                     'comp': c.get('completion_tokens_est', 0)})
    arch_t = total_of(calls)
    new_t = sum(p + r['comp'] for p, r in zip(sim_new, rows))
    out['arms'][arm] = {'calls': len(calls), 'archived_total': arch_t, 'repro_ok': rec == [c['prompt_tokens_est'] for c in calls],
                        'pred_total_after_fix': new_t, 'rows': rows}

a = out['arms']['A']; b = out['arms']['BRJ']
out['pred_drop_pct'] = round((a['archived_total'] - b['pred_total_after_fix']) / a['archived_total'] * 100, 2)
out['r436_drop_pct'] = round((a['archived_total'] - b['archived_total']) / a['archived_total'] * 100, 2)
out['saved_tokens'] = b['archived_total'] - b['pred_total_after_fix']
out['A_invariance_expected'] = a['archived_total'] == a['pred_total_after_fix']

with open(os.path.join(D, 'predict-r438.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

for arm in ('A', 'BRJ'):
    x = out['arms'][arm]
    print(f"[{arm}] calls={x['calls']} archived={x['archived_total']} repro_ok={x['repro_ok']} pred_after_fix={x['pred_total_after_fix']}")
    for r in x['rows']:
        print(f"    call{r['call']:2d} nmsg={r['nmsg']:2d} archived={r['archived']:5d} repro={r['repro_from_chars']:5d} pred={r['pred_after_fix']:5d}")
print(f"R436 measured drop (BRJ vs A) = {out['r436_drop_pct']}%")
print(f"R438 PREDICTED drop (BRJ vs A) = {out['pred_drop_pct']}%   saved={out['saved_tokens']} tok   A_invariance={out['A_invariance_expected']}")
