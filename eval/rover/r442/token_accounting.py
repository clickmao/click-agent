#!/usr/bin/env python3
"""R442 器具 — ① **口径钉死**（远端-only vs 含本地 r1）② **两臂内联块不对称定量**（R441 挂账 #1）。

数据源（全部为 R441 已落盘真机档案, 本轮零新测量）:
  * `eval/rover/r441/verdict-{A,BRJ}-{g}.json`   —— 远端真值: G_tokens/J_tokens/per_turn/judge_local_tokens
  * `eval/rover/r441/run-{arm}-{g}/data/telemetry/host.jsonl` —— 本地 r1 明细:
      local_turn_gate{gate_prompt_len, raw_len}（本地门的提示字符数 + 本地生成长度）
      correction_judge{source, tokens}（判官; source=local 才算本地成本）
  * `eval/rover/r441/calls-{A,BRJ}-{g}.jsonl` —— 逐请求 messages 全文 ⇒ 可切出「内联块」，用于不对称定量

口径三档（同一批档案, 只换分母/加项, 不改被测）:
  D_remote : 1 − ΣG_B / ΣG_A                     （R436–R441 沿用的口径；只算远端主生成）
  D_rl     : 1 − (ΣG+local)_B / (ΣG+local)_A     （含本地 r1: 门提示+门生成+本地判官）
  D_rj     : 1 − (ΣG+ΣJ+local)_B / (ΣG+ΣJ+local)_A（再把远端判官请求计入——本轮网格 J 为 0）

本地 token 折算**显式声明**: `chars/2`（与桩侧 estimator 同源; 非 tokenizer 真值 ⇒ 在诚实边界登记）。
不对称定量: 逐主调用比较两臂"该轮历史 user 消息里附加块"的 token 数 ⇒ Δ(i) = block_B(t) − block_A(t);
  对 BRJ 臂每个主调用累加 Σ_{t<i}Δ(t) 得该调用的「块不对称放大量」; 校正降幅 = 1 − (G_B − Σasym)/G_A。
"""
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
D = ROOT / 'eval/rover/r441'
OUT = ROOT / 'eval/rover/r442'
GRIDS = ('W8', 'W20', 'M20')
CHARS_PER_TOK = 2.0          # 显式声明的折算（与桩 estimator 同源）


def load(p):
    p = pathlib.Path(p)
    return json.load(open(p, encoding='utf-8')) if p.exists() else None


def calls(p):
    p = pathlib.Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]


def telemetry(run):
    p = D / run / 'data/telemetry/host.jsonl'
    out = []
    if not p.exists():
        return out
    for l in open(p, encoding='utf-8-sig', errors='replace'):
        l = l.strip()
        if l:
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    return out


def local_cost(run):
    """本地 r1 成本（token）: 门(提示+生成) + 本地判官生成。返回明细以便审计。"""
    recs = telemetry(run)
    gate = [r['kv'] for r in recs if r.get('point') == 'local_turn_gate']
    r1 = [g for g in gate if int(g.get('gate_prompt_len') or 0) > 0]
    gate_chars = sum(int(g.get('gate_prompt_len') or 0) for g in r1)
    gen_chars = sum(int(g.get('raw_len') or 0) for g in r1)
    judges = [r['kv'] for r in recs if r.get('point') == 'correction_judge']
    j_local_tok = sum(int(j.get('tokens') or 0) for j in judges if j.get('source') == 'local')
    j_local_n = sum(1 for j in judges if j.get('source') == 'local')
    j_remote_n = sum(1 for j in judges if j.get('source') != 'local' and int(j.get('tokens') or 0) > 0)
    gate_tok = (gate_chars + gen_chars) / CHARS_PER_TOK
    return {'r1_gate_calls': len(r1), 'gate_prompt_chars': gate_chars, 'gate_gen_chars': gen_chars,
            'gate_tokens_est': round(gate_tok, 1), 'judge_local_calls': j_local_n,
            'judge_local_tokens': j_local_tok, 'judge_nonlocal_with_tokens': j_remote_n,
            'local_total_tokens': round(gate_tok + j_local_tok, 1)}


def arm_verdict(g, arm, sfx=''):
    v = load(D / f'verdict-{arm}-{g}{sfx}.json')
    return v


def sfx_for(g):
    for s in ('', '-b2', '-c2'):
        if (D / f'verdict-BRJ-{g}{s}.json').exists() and (D / f'verdict-A-{g}{s}.json').exists():
            return s
    return ''


def block_tokens_by_turn(arm, g, sfx, turns):
    """逐「主调用」的历史 user 条目: 该条目 = 网格原文 + 附加块 ⇒ 返回 {turn: [块 token, ...]}（token = 字符/2）。"""
    recs = calls(D / f'calls-{arm}-{g}{sfx}.jsonl')
    out = {}
    for r in recs:
        nm = int(r.get('n_messages') or 0)
        if nm < 4 or nm % 2 != 0:
            continue
        i = nm // 2                      # 当前轮
        if not (1 <= i <= len(turns)):
            continue
        for idx, m in enumerate(r.get('messages') or []):
            if m.get('role') != 'user' or idx == nm - 1:
                continue
            t = (idx + 1) // 2
            if not (1 <= t <= len(turns)):
                continue
            c = m.get('content') or ''
            txt = turns[t - 1]
            if txt not in c:
                continue
            blk = c[c.index(txt) + len(txt):]
            if blk.strip():
                out.setdefault(t, []).append(len(blk) / CHARS_PER_TOK)
    return {t: statistics.median(v) for t, v in out.items()}


def asymmetry(g, sfx, turns):
    """两臂不对称: 对 BRJ 每个主调用累加 Σ_{t<i} [block_B(t) − block_A(t)]。"""
    bB = block_tokens_by_turn('BRJ', g, sfx, turns)
    bA = block_tokens_by_turn('A', g, sfx, turns)
    recs_b = calls(D / f'calls-BRJ-{g}{sfx}.jsonl')
    per_call = []
    for r in recs_b:
        nm = int(r.get('n_messages') or 0)
        if nm < 4 or nm % 2 != 0:
            continue
        i = nm // 2
        if not (1 <= i <= len(turns)):
            continue
        d = sum(bB.get(t, 0.0) - bA.get(t, 0.0) for t in range(1, i))
        if d:
            per_call.append({'turn': i, 'asym_tok': round(d, 1)})
    return {'block_A_median_tok': {t: round(v, 1) for t, v in sorted(bA.items())},
            'block_B_median_tok': {t: round(v, 1) for t, v in sorted(bB.items())},
            'per_main_call': per_call, 'asym_total_tok': round(sum(x['asym_tok'] for x in per_call), 1)}


def main():
    rep = {'round': 'R442', 'kind': 'accounting_and_asymmetry',
           'estimator': {'local_chars_per_token': CHARS_PER_TOK,
                         'note': '本地侧由字符数折算（与桩 estimator 同源），非 tokenizer 真值'},
           'grids': {}}
    for g in GRIDS:
        spec = load(D / f'grid/task-{g}.json')
        if not spec:
            rep['grids'][g] = 'NO_GRID'
            continue
        sfx = sfx_for(g)
        va, vb = arm_verdict(g, 'A', sfx), arm_verdict(g, 'BRJ', sfx)
        if not (va and vb):
            rep['grids'][g] = 'NO_DATA'
            continue
        la = local_cost(f'run-A-{g}{sfx}')
        lb = local_cost(f'run-BRJ-{g}{sfx}')
        gA, gB = va['G_tokens'], vb['G_tokens']
        jA, jB = va.get('J_tokens', 0), vb.get('J_tokens', 0)
        d_remote = 100 * (1 - gB / gA)
        d_rl = 100 * (1 - (gB + lb['local_total_tokens']) / (gA + la['local_total_tokens']))
        d_rj = 100 * (1 - (gB + jB + lb['local_total_tokens']) / (gA + jA + la['local_total_tokens']))
        asym = asymmetry(g, sfx, spec['turns'])
        b_sym = gB - asym['asym_total_tok']
        d_sym = 100 * (1 - b_sym / gA)
        rep['grids'][g] = {
            'sfx': sfx, 'N': len(spec['turns']),
            'skips': sorted(t for t, r in {r['turn']: r for r in vb['per_turn']}.items() if r.get('actual') == 'skip'),
            'remote_G': {'A': gA, 'B': gB, 'saved': gA - gB},
            'remote_J': {'A': jA, 'B': jB},
            'local_A': la, 'local_B': lb,
            'drops_pct': {'D_remote': round(d_remote, 4), 'D_remote_plus_local': round(d_rl, 4),
                          'D_remote_J_local': round(d_rj, 4),
                          'D_remote_symmetrised': round(d_sym, 4),
                          'incremental_local_cost_tok': round(lb['local_total_tokens'], 1)},
            'asymmetry': asym,
        }
        print(f"[{g}] N={len(spec['turns'])} skips={rep['grids'][g]['skips']} "
              f"A={gA} B={gB} local_B={lb['local_total_tokens']} | D_remote={d_remote:.2f}% "
              f"D_rl={d_rl:.2f}% | asym={asym['asym_total_tok']} ⇒ D_sym={d_sym:.2f}%")
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(OUT / 'accounting-r442.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('wrote', OUT / 'accounting-r442.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
