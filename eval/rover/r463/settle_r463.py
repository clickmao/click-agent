#!/usr/bin/env python3
"""R463 结算 — 3B 判别通道采用验证（承重: 用户一轮 total API token 降幅 / 质量不退化）。

外部真值（不信被测量自报）:
  (1) 桩侧 calls jsonl —— 逐请求落盘 seq/ts/prompt_tokens_est/completion_tokens_est ⇒ **远端 API 请求数/token**;
  (2) 逐轮 turns jsonl —— t_start/t_end（顺序分区）+ reply 原文（回复面）;
  (3) 产品遥测 point=local_turn_gate —— 门判走向 (verdict/basis/raw/gen) 与本地成本（不计入 API token）。

口径:
  · token 估计来自桩侧分词启发式 (prompt_tokens_est) ⇒ **同桩同估计器**, 跨臂可比; 绝对值不作宣称;
  · 归因: 每条远端调用按 ts 落入 [t_start, t_end] 的轮窗口 (顺序分区, R425 纪律);
  · 降幅 = 1 − Σtok(臂) / Σtok(A 臂, 同网格同二进制);
  · 质量面: 残余带轮 (6–9) / 纠正轮 (10–12) 若 verdict=Skip ⇒ 记 quality_risk。
用法: python3 settle_r463.py <run_root> [A_分母tok]
"""
import glob
import io
import json
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '/home/agentuser/AgentFramework/eval/rover/r463'
DENOM = None
if len(sys.argv) > 2 and sys.argv[2] not in ('', '-'):
    DENOM = float(sys.argv[2])

RISK_TURNS = set(range(6, 13))   # 残余带 + 纠正轮: 真诉求 ⇒ 不得 Skip


def calls_of(arm):
    p = os.path.join(ROOT, f'calls-{arm}.jsonl')
    if not os.path.exists(p):
        return None
    out = []
    for line in io.open(p, encoding='utf-8'):
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def turns_of(arm):
    p = os.path.join(ROOT, f'turns-{arm}.jsonl')
    if not os.path.exists(p):
        return []
    try:
        d = json.load(io.open(p, encoding='utf-8'))
    except Exception:
        return []
    if isinstance(d, dict):
        return d.get('turns') or []
    return d if isinstance(d, list) else []


def gate_events(arm):
    p = os.path.join(ROOT, f'run-{arm}', 'data', 'telemetry', 'host.jsonl')
    ev = []
    if not os.path.exists(p):
        return ev
    for line in io.open(p, encoding='utf-8', errors='replace'):
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get('point') in ('local_turn_gate', 'local_turn_gate_reject', 'local_turn_gate_config'):
            ev.append((d.get('point'), d.get('kv') or {}))
    return ev


def summarise(arm):
    cs = calls_of(arm)
    ts = turns_of(arm)
    if cs is None:
        return {'arm': arm, 'status': 'MISSING_CALLS'}
    pin = sum(int(c.get('prompt_tokens_est') or 0) for c in cs)
    cout = sum(int(c.get('completion_tokens_est') or 0) for c in cs)
    # 归因: 调用 ts → 轮窗口
    per_turn = {t.get('turn'): 0 for t in ts}
    for c in cs:
        try:
            cts = float(c.get('ts') or 0)
        except (TypeError, ValueError):
            continue
        for t in ts:
            a, b = t.get('t_start'), t.get('t_end')
            if a is None or b is None:
                continue
            if float(a) - 0.25 <= cts <= float(b) + 0.25:
                per_turn[t.get('turn')] = per_turn.get(t.get('turn'), 0) + 1
                break
    gev = gate_events(arm)
    gates = [{'verdict': k.get('verdict'), 'basis': k.get('basis'),
              'raw_len': k.get('raw_len'), 'gen_tokens': k.get('gen_tokens'),
              'tokens_evaluated': k.get('tokens_evaluated'),
              'prompt_len': k.get('gate_prompt_len')}
             for pt, k in gev if pt == 'local_turn_gate']
    rej = sum(1 for pt, _ in gev if pt == 'local_turn_gate_reject')
    cfg = next((k for pt, k in gev if pt == 'local_turn_gate_config'), {})
    risk = []
    for i, t in enumerate(ts, 1):
        v = gates[i - 1]['verdict'] if i - 1 < len(gates) else None
        if v == 'Skip' and i in RISK_TURNS:
            risk.append({'turn': i, 'verdict': v, 'basis': gates[i - 1]['basis'],
                         'text': (t.get('text') or '')[:30], 'reply': (t.get('reply') or '')[:40]})
    return {
        'arm': arm,
        'calls': len(cs),
        'prompt_tokens_est': pin,
        'completion_tokens_est': cout,
        'total_tokens_est': pin + cout,
        'per_turn_calls': per_turn,
        'gate_events': len(gates),
        'gate_verdicts': [g['verdict'] for g in gates],
        'gate_bases': [g['basis'] for g in gates],
        'gate_local_tokens_evaluated': sum(int(g['tokens_evaluated'] or 0) for g in gates if str(g['tokens_evaluated'] or '').lstrip('-').isdigit()),
        'gate_local_gen_tokens': sum(int(g['gen_tokens'] or 0) for g in gates if str(g['gen_tokens'] or '').lstrip('-').isdigit()),
        'skip_rejected': rej,
        'local_channel_ready': cfg.get('local_channel_ready'),
        'turn_gate_enabled': cfg.get('turn_gate_enabled'),
        'quality_risk': risk,
        'turns_ok': sum(1 for t in ts if t.get('ok')),
        'replies': [{'turn': t.get('turn'), 'text': (t.get('text') or '')[:40],
                     'reply': (t.get('reply') or '')[:60], 'reply_len': len(t.get('reply') or '')} for t in ts],
    }


def main():
    arms = sys.argv[3].split(',') if len(sys.argv) > 3 else ['A', 'B15', 'B3B', 'BP']
    res = {}
    for a in arms:
        r = summarise(a)
        res[a] = r
        print(f"[{a}] calls={r.get('calls')} tok={r.get('total_tokens_est')} "
              f"gate={r.get('gate_events')} verdicts={r.get('gate_verdicts')} "
              f"rej={r.get('skip_rejected')} risk={len(r.get('quality_risk') or [])} turns_ok={r.get('turns_ok')}")
    a_tok = (res.get('A') or {}).get('total_tokens_est')
    for a, r in res.items():
        if a_tok and r.get('total_tokens_est') is not None and a != 'A':
            r['drop_vs_A'] = round(1 - r['total_tokens_est'] / a_tok, 4)
            print(f"  {a}: 降幅 = {r['drop_vs_A']*100:.2f}%  (A 分母 {a_tok})")
    out = os.path.join(ROOT, 'verdict-r463.json')
    io.open(out, 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=1))
    print('->', out)


if __name__ == '__main__':
    main()
