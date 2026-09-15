#!/usr/bin/env python3
"""R464 结算 — 本地判别通道「配置错配 fail-closed」（承重: ①错配不再静默 ②主判据降幅 ≥30% ③质量不退化）。

外部真值（不信被测量自报）:
  (1) 桩侧 calls jsonl —— 逐请求 seq/ts/prompt_tokens_est/completion_tokens_est ⇒ **远端 API 请求数/token**;
  (2) 逐轮 turns jsonl —— t_start/t_end（顺序分区）+ reply 原文（回复面）;
  (3) 产品遥测 point=local_turn_gate / local_turn_gate_config —— 门判走向与本地成本;
  (4) 宿主 stderr 日志的 ASCII 告警标记 `R464 config_mismatch:` / `R464 config_default_missing:`。

口径:
  · token 估计来自桩侧分词启发式 (prompt_tokens_est) ⇒ **同桩同估计器**, 跨臂可比; 绝对值不作宣称;
  · 归因: 每条远端调用按 ts 落入 [t_start, t_end] 的轮窗口 (顺序分区, R425 纪律);
  · 主判据分母 = **Arole**（门关 + role on，与 B3B 逐字同 role）; 旧 A（无 role）仅作对齐 R463 的副读数;
  · 质量面: 残余带轮 (6–9) / 纠正轮 (10–12) 若 verdict=Skip ⇒ 记 quality_risk。

用法: python3 settle_r464.py <run_root> <arm>            # 逐臂累加进 verdict-r464.json
      python3 settle_r464.py <run_root> --all            # 重算全部已跑臂 + 判定
"""
import glob
import io
import json
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '/home/agentuser/AgentFramework/eval/rover/r464'
ARMS_ALL = ['Arole', 'B3B', 'BP', 'BP2']
DENOM_PRIMARY = 'Arole'
DENOM_LEGACY = 'A'
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


def _num(v):
    """只有真数字（含 0）才算读数; '-1'/'-8' 是「非本地调用」哨兵, 不得混入求和 (R464 修: 旧版把哨兵当读数累计)。"""
    s = str(v if v is not None else '').strip()
    return int(s) if s.lstrip('-').isdigit() and int(s) >= 0 else None


def _sum_ok(vals):
    vals = [v for v in vals if v is not None]
    return (sum(vals), len(vals)) if vals else (0, 0)


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


def host_log(arm):
    p = os.path.join(ROOT, f'host-{arm}.log')
    if not os.path.exists(p):
        return ''
    return io.open(p, encoding='utf-8', errors='replace').read()


def warn_scan(arm):
    txt = host_log(arm)
    return {
        'config_mismatch': txt.count('R464 config_mismatch:'),
        'config_default_missing': txt.count('R464 config_default_missing:'),
        'lines': [l.strip() for l in txt.splitlines() if 'R464 config_' in l][:4],
    }


def summarise(arm):
    cs = calls_of(arm)
    ts = turns_of(arm)
    if cs is None:
        return {'arm': arm, 'status': 'MISSING_CALLS'}
    pin = sum(int(c.get('prompt_tokens_est') or 0) for c in cs)
    cout = sum(int(c.get('completion_tokens_est') or 0) for c in cs)
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
        'gate_local_tokens_evaluated': _sum_ok([_num(g['tokens_evaluated']) for g in gates])[0],
        'gate_local_tokens_evaluated_n': _sum_ok([_num(g['tokens_evaluated']) for g in gates])[1],
        'gate_local_gen_tokens': _sum_ok([_num(g['gen_tokens']) for g in gates])[0],
        'gate_local_gen_tokens_n': _sum_ok([_num(g['gen_tokens']) for g in gates])[1],
        'gate_local_decisions': sum(1 for g in gates if '→local' in str(g['basis'])),
        'gate_degraded_remote': sum(1 for g in gates if 'degraded' in str(g['basis'])),
        'gate_bases_full': [g['basis'] for g in gates],
        'skip_rejected': rej,
        'local_channel_ready': cfg.get('local_channel_ready'),
        'turn_gate_enabled': cfg.get('turn_gate_enabled'),
        'quality_risk': risk,
        'turns_ok': sum(1 for t in ts if t.get('ok')),
        'warn_scan': warn_scan(arm),
        'replies': [{'turn': t.get('turn'), 'text': (t.get('text') or '')[:40],
                     'reply': (t.get('reply') or '')[:60], 'reply_len': len(t.get('reply') or '')} for t in ts],
    }


def load_verdict():
    p = os.path.join(ROOT, 'verdict-r464.json')
    if os.path.exists(p):
        try:
            return json.load(io.open(p, encoding='utf-8'))
        except Exception:
            return {}
    return {}


def save_verdict(res):
    p = os.path.join(ROOT, 'verdict-r464.json')
    io.open(p, 'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=1))
    return p


def evaluate(res):
    """判据 C1–C7 的机检面（只读档案, 不作事后裁剪）。"""
    claims = {}

    def tok(a):
        return (res.get(a) or {}).get('total_tokens_est')

    a_pri, a_leg = tok(DENOM_PRIMARY), tok(DENOM_LEGACY)
    b = tok('B3B')
    if a_pri and b:
        claims['C5'] = {'pass': (1 - b / a_pri) >= 0.30,
                        'drop_vs_Arole': round(1 - b / a_pri, 4), 'denom': a_pri}
    if a_leg and b:
        claims['C5_legacy'] = {'drop_vs_A': round(1 - b / a_leg, 4), 'denom_A': a_leg,
                               'note': 'R463 口径（分母未带 role）仅供对齐'}
    if a_pri and a_leg:
        claims['role_block_cost'] = {'tokens': a_pri - a_leg,
                                     'pct_of_Arole': round(1 - a_leg / a_pri, 4)}

    bp, bp2 = res.get('BP') or {}, res.get('BP2') or {}
    # C3: 错配臂必须留告警
    claims['C3'] = {'pass': (bp.get('warn_scan', {}).get('config_mismatch', 0) or 0) > 0,
                    'bp_warn': bp.get('warn_scan'), 'bp2_warn': bp2.get('warn_scan')}
    # C4: 不再静默等价 —— BP 读数必须与 B3B 不同（本地通道必须真的没跑）
    if bp.get('total_tokens_est') is not None and b is not None:
        same = (bp.get('total_tokens_est') == b and bp.get('calls') == (res.get('B3B') or {}).get('calls')
                and bp.get('gate_verdicts') == (res.get('B3B') or {}).get('gate_verdicts'))
        claims['C4'] = {'pass': not same, 'bp_tok': bp.get('total_tokens_est'), 'b3b_tok': b,
                        'bp_gate_events': bp.get('gate_events'), 'b3b_gate_events': (res.get('B3B') or {}).get('gate_events'),
                        'identical_to_B3B': same}
    # C6: 真缺模型 ⇒ 门零决策 + 不崩 + 告警可见
    if bp2:
        claims['C6'] = {'pass': (bp2.get('gate_events') or 0) == 0
                                and (bp2.get('warn_scan', {}).get('config_mismatch', 0) or 0) > 0
                                and (bp2.get('turns_ok') or 0) > 0,
                        'gate_events': bp2.get('gate_events'), 'turns_ok': bp2.get('turns_ok')}
    # 质量面: 门开的臂不得在残余带/纠正轮 Skip
    for a in ('B3B', 'BP', 'BP2'):
        r = res.get(a)
        if r:
            claims[f'quality_{a}'] = {'pass': len(r.get('quality_risk') or []) == 0 and (r.get('turns_ok') or 0) == 12,
                                      'risk': r.get('quality_risk'), 'turns_ok': r.get('turns_ok')}
    # 确定性: 同二进制同配置两跑（由 harness 外的复跑臂提供, 此处仅登记口径）
    claims['determinism_note'] = {'rule': '同臂复跑须逐位相同（gen/verdicts/tokens）; 本表不含复跑臂'}
    return claims


def posthoc(res):
    """事后判据（单列, 不改写预注册结果）:
       C6'  = 预注册 C6 口径写错（我把它定义成 gate_events==0, 产品语义实为「零本地判决」）⇒ 正确形态单列;
       C8   = 跨版本确定性: 真不可用路径 R464 读数须与 R463 逐位一致（改动零回归）;
       C9   = 本地承重证据: 门开臂的 Skip 轮必须真的在本地算了（eval/gen 正数）, 不是「跳过=空跑」。
    """
    out = {}
    bp, bp2, b3b = res.get('BP') or {}, res.get('BP2') or {}, res.get('B3B') or {}
    for a, r in (('BP', bp), ('BP2', bp2)):
        if not r:
            continue
        out[f"C6'_zero_local_{a}"] = {
            'pass': (r.get('gate_local_decisions') or 0) == 0
                    and (r.get('gate_local_tokens_evaluated') or 0) == 0
                    and (r.get('gate_local_gen_tokens') or 0) == 0
                    and 'Skip' not in (r.get('gate_verdicts') or [])
                    and (r.get('turns_ok') or 0) == 12
                    and (r.get('warn_scan', {}).get('config_mismatch') or 0) > 0,
            'local_decisions': r.get('gate_local_decisions'), 'local_eval': r.get('gate_local_tokens_evaluated'),
            'local_gen': r.get('gate_local_gen_tokens'), 'degraded_remote': r.get('gate_degraded_remote'),
            'skips': (r.get('gate_verdicts') or []).count('Skip'), 'turns_ok': r.get('turns_ok'),
            'warns': r.get('warn_scan', {}).get('config_mismatch'),
        }
    r463 = {}
    p463 = os.path.join(os.path.dirname(ROOT.rstrip('/')), 'r463', 'verdict-r463.json')
    if os.path.exists(p463):
        try:
            r463 = json.load(io.open(p463, encoding='utf-8'))
        except Exception:
            r463 = {}
    d463 = r463.get('BP2') or {}
    if d463 and bp2:
        same = (d463.get('calls') == bp2.get('calls') and d463.get('total_tokens_est') == bp2.get('total_tokens_est'))
        out['C8_cross_round_determinism'] = {
            'pass': bool(same), 'r463_BP2': [d463.get('calls'), d463.get('total_tokens_est')],
            'r464_BP2': [bp2.get('calls'), bp2.get('total_tokens_est')],
            'note': '真不可用路径（双缺模型）跨版本读数须逐位相同 ⇒ 证明 fail-closed 改造未改动降级路径',
        }
    d463b = r463.get('B3B') or {}
    if not d463b:
        # R463 verdict 只落了 A/BP/BP2; B3B 读数从原始桩侧 calls 档直接重算（外部真值, 不看自报）
        pc = os.path.join(os.path.dirname(ROOT.rstrip('/')), 'r463', 'calls-B3B.jsonl')
        if os.path.exists(pc):
            cs = [json.loads(l) for l in io.open(pc, encoding='utf-8') if l.strip()]
            d463b = {'calls': len(cs),
                     'total_tokens_est': sum(int(c.get('prompt_tokens_est') or 0) + int(c.get('completion_tokens_est') or 0) for c in cs),
                     'source': 'recomputed_from_calls-B3B.jsonl'}
    if d463b and b3b:
        out['C8b_B3B_reproducibility'] = {
            'pass': bool(d463b.get('calls') == b3b.get('calls')
                         and abs((d463b.get('total_tokens_est') or 0) - (b3b.get('total_tokens_est') or 0)) <= 0),
            'r463_B3B': [d463b.get('calls'), d463b.get('total_tokens_est')],
            'r464_B3B': [b3b.get('calls'), b3b.get('total_tokens_est')],
            'note': '门开臂跨版本重跑同读数 ⇒ 本地通道增益可复现',
        }
    if b3b:
        out['C9_local_bearing'] = {
            'pass': (b3b.get('gate_local_decisions') or 0) > 0
                    and (b3b.get('gate_local_tokens_evaluated') or 0) > 0
                    and (b3b.get('gate_local_gen_tokens') or 0) > 0
                    and (b3b.get('gate_local_tokens_evaluated_n') or 0) == (b3b.get('gate_local_decisions') or 0),
            'local_decisions': b3b.get('gate_local_decisions'),
            'local_eval_tokens': b3b.get('gate_local_tokens_evaluated'),
            'local_gen_tokens': b3b.get('gate_local_gen_tokens'),
            'note': 'Skip 轮必须留下本地真实算力读数（eval>0, gen>0）——证「本地判决」而非「空跳过」',
        }
    a_pri = (res.get(DENOM_PRIMARY) or {}).get('total_tokens_est')
    if a_pri and bp and b3b:
        out['C10_available_vs_mismatch_same_grid'] = {
            'pass': (1 - (b3b.get('total_tokens_est') or 0) / max(bp.get('total_tokens_est') or 1, 1)) >= 0.30,
            'drop_vs_BP': round(1 - (b3b.get('total_tokens_est') or 0) / max(bp.get('total_tokens_est') or 1, 1), 4),
            'denom': bp.get('total_tokens_est'),
            'note': '单一变量分母族: BP 与 B3B 同 role/同 RJ/同网格, 仅「本地通道可用性」不同（承 R463 §负控口径）',
        }
    return out


def main():
    arms = ARMS_ALL if (len(sys.argv) > 2 and sys.argv[2] == '--all') else [(sys.argv[2] if len(sys.argv) > 2 else 'Arole')]
    res = load_verdict()
    for a in arms:
        r = summarise(a)
        res[a] = r
        if r.get('status') != 'MISSING_CALLS':
            print(f"[{a}] calls={r.get('calls')} tok={r.get('total_tokens_est')} "
                  f"gate={r.get('gate_events')} verdicts={r.get('gate_verdicts')} "
                  f"rej={r.get('skip_rejected')} risk={len(r.get('quality_risk') or [])} "
                  f"turns_ok={r.get('turns_ok')} warns={r.get('warn_scan', {}).get('config_mismatch')}")
    res['claims'] = evaluate(res)
    res['checks_posthoc'] = posthoc(res)
    p = save_verdict(res)
    for k in sorted(c for c in res['claims'] if c.startswith('C')):
        c = res['claims'][k]
        if isinstance(c, dict) and 'pass' in c:
            print(f"  {k}: {'PASS' if c['pass'] else 'FAIL'} {json.dumps({x: y for x, y in c.items() if x != 'pass'}, ensure_ascii=False)}")
    for k, c in res['checks_posthoc'].items():
        print(f"  [posthoc] {k}: {'PASS' if c['pass'] else 'FAIL'} {json.dumps({x: y for x, y in c.items() if x != 'pass'}, ensure_ascii=False)}")
    print('->', p)


if __name__ == '__main__':
    main()
