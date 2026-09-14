#!/usr/bin/env python3
"""R441 同网格弃块质量直接量测（事后器具）— 替代 R440 的跨网格 m 中位 + λ 标定。

动机: 预注册预测器用「位置->块质量」中位(源自 p8/p12 存档)+λ=0.766, 在 M20 上仍差 3.8pt。
直读 A 臂 calls 后发现: 块质量不是位置函数, 而是**该轮历史里累积的[已完成]条目**的函数
(条目随会话推进增长) => 同网格直接量测块字符长度(turn 文本之后的附加段)才是正确器具。

判据(机械):
  M1 每个主调用的历史 user 消息 = 网格该轮原文 + 附加块(可前缀/后缀包裹) => 逐条可切分
  M2 用实测块质量算 B_pred, 与 B 实测比对: |Δdrop| <= 1.5pt 记 OK
输出: blockmass-r441.json (各网格 block_tok[t], removal 汇总, 残差)
"""
import json, pathlib, statistics, sys

D = pathlib.Path('/home/agentuser/AgentFramework/eval/rover/r441')
G = ('W8', 'W20', 'M20', 'V2b')


def load(p):
    p = pathlib.Path(p)
    if not p.exists():
        return None
    return json.load(open(p, encoding='utf-8'))


def grid(g):
    return load(D / f'grid/task-{g}.json')


def calls(p):
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()] if pathlib.Path(p).exists() else []


def arms(g):
    for sfx in ('', '-b2'):
        a, b = load(D / f'verdict-A-{g}{sfx}.json'), load(D / f'verdict-BRJ-{g}{sfx}.json')
        if a and b:
            return sfx, a, b
    return '', load(D / f'verdict-A-{g}.json'), load(D / f'verdict-BRJ-{g}.json')


def block_tok_by_turn(g, sfx, turns):
    """对每个主调用(2*i 条消息)读出历史 user 消息的附加块字符数 -> {turn: [块 tok, ...]}"""
    recs = calls(D / f'calls-A-{g}{sfx}.jsonl')
    out = {}
    for r in recs:
        nm = r['n_messages']
        if nm < 4:
            continue
        i = nm // 2
        if not (1 <= i <= len(turns)):
            continue
        want = turns[i - 1]
        for idx, m in enumerate(r['messages']):
            c = m.get('content') or ''
            if m.get('role') != 'user' or idx == nm - 1:
                continue
            t = (idx + 1) // 2                      # 历史条目 t (1..i-1)
            if not (1 <= t <= len(turns)):
                continue
            txt = turns[t - 1]
            if txt not in c:
                continue
            j = c.index(txt) + len(txt)
            blk = c[j:]
            if blk.strip():
                out.setdefault(t, []).append(len(blk) // 2)
    return out


def main():
    rep = {'round': 'r441', 'kind': 'POSTHOC_same_grid_block_mass'}
    for g in G:
        spec = grid(g)
        if not spec:
            rep[g] = 'NO_GRID'
            continue
        sfx, va, vb = arms(g)
        if not (va and vb):
            rep[g] = 'NO_DATA'
            continue
        turns = spec['turns']
        bt = block_tok_by_turn(g, sfx, turns)
        med = {t: int(statistics.median(v)) for t, v in bt.items()}
        pa = {r['turn']: r for r in va['per_turn']}
        pb = {r['turn']: r for r in vb['per_turn']}
        S = sorted(t for t, r in pb.items() if r.get('actual') == 'skip')
        tot_a, tot_b = va['tokens_total'], vb['tokens_total']
        n_main_b = sum(1 for r in vb['per_turn'] if int(r.get('G_calls') or 0) > 0 and r.get('actual') != 'skip')
        rho = sum(int(pb[t].get('G_tokens') or 0) for t in S)
        removal = 0.0
        for i in sorted(pb):
            if i in S:
                continue
            if int(pb[i].get('G_calls') or 0) == 0:
                continue
            removal += sum(med.get(t, 0) for t in S if t < i)
        b_pred = sum(int(pa[i].get('G_tokens') or 0) for i in sorted(pa) if i not in S) + 77 * n_main_b + rho - removal
        d_meas = 100 * (1 - tot_b / tot_a)
        d_pred = 100 * (1 - b_pred / tot_a)
        rep[g] = {'sfx': sfx, 'S': S, 'block_tok_median': {str(k): v for k, v in sorted(med.items())},
                  'n_main_B': n_main_b, 'rho_total': rho, 'removal_total': round(removal, 1),
                  'A_total': tot_a, 'B_total': tot_b, 'B_pred': round(b_pred, 1),
                  'drop_meas_pct': round(d_meas, 2), 'drop_pred_pct': round(d_pred, 2),
                  'dev_pt': round(abs(d_meas - d_pred), 2),
                  'verdict': 'OK' if abs(d_meas - d_pred) <= 1.5 else 'WARN'}
        print(f'[{g}] {rep[g]}')
    (D / 'blockmass-r441.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
    print('[blockmass] wrote', D / 'blockmass-r441.json')


if __name__ == '__main__':
    sys.exit(main())
