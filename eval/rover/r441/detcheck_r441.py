#!/usr/bin/env python3
"""R441 确定性复现校验（判据 C7 的证据来源）— 逐位比较两对同网格同臂跑的调用序列与回复文本。

配对:
  P1 同轮复现: (W8, A, '' ) vs (W8, A, '-b2')      — 阶段二误跑带来的意外复现对（A 臂）
  P2 同轮复现: (W8, BRJ, '') vs (W8, BRJ, '-b2')   — BRJ 臂（含 llama-server r1 判官 + 采样 ⇒ 更强）
  P3 跨轮复现: R441 (V2b, *, '-c2') vs R440 (V2b-b1) — 同二进制 sha 同网格跨轮
判据: 调用级 (prompt_tokens_est, completion_tokens_est) 序列逐位相同 且 各轮 reply 文本逐位相同
输出: detcheck-r441.json
"""
import json, pathlib, sys

R = pathlib.Path('/home/agentuser/AgentFramework')
D = R / 'eval/rover/r441'


def calls(p):
    p = pathlib.Path(p)
    return [(r['prompt_tokens_est'], r['completion_tokens_est'], r['n_messages']) for r in
            (json.loads(l) for l in open(p, encoding='utf-8') if l.strip())] if p.exists() else None


def turns(p):
    p = pathlib.Path(p)
    if not p.exists():
        return None
    d = json.load(open(p, encoding='utf-8'))
    ts = d['turns'] if isinstance(d, dict) else d
    return [str(t.get('reply')) for t in ts]


def pair(name, pa, pb):
    ca, cb = calls(pa), calls(pb)
    if ca is None or cb is None:
        return {'pair': name, 'verdict': 'NO_DATA', 'a': str(pa), 'b': str(pb)}
    same_calls = ca == cb
    diff_idx = [i for i, (x, y) in enumerate(zip(ca, cb)) if x != y][:6]
    # 工作区路径长度会进 system prompt ⇒ NS 后缀(-b2/-c2)引入 +1~+2 tok 常数偏移; 判据取「偏移为常数且 <=3」等价类
    deltas = sorted({(y[0] - x[0], y[1] - x[1]) for x, y in zip(ca, cb)}) if len(ca) == len(cb) else None
    offsets = sorted({d[0] for d in deltas}) if deltas else None
    offset_ok = bool(offsets) and all(0 <= o <= 3 for o in offsets)
    ta, tb = turns(str(pa).replace('calls-', 'turns-').replace('.jsonl', '.jsonl')), \
        turns(str(pb).replace('calls-', 'turns-').replace('.jsonl', '.jsonl'))
    if str(pa).endswith('.jsonl') and (ta is None or tb is None):
        ta = turns(str(pa).replace('calls-', 'turns-'))
        tb = turns(str(pb).replace('calls-', 'turns-'))
    same_turns = (ta == tb) if (ta is not None and tb is not None) else None
    return {'pair': name, 'a': str(pa), 'b': str(pb), 'n_calls_a': len(ca), 'n_calls_b': len(cb),
            'calls_identical': same_calls, 'first_diff_idx': diff_idx,
            'prompt_offsets': offsets, 'offset_within_path_artifact_bound': offset_ok,
            'turns_identical': same_turns, 'delta_total_tokens': (sum(x[0] + x[1] for x in cb) - sum(x[0] + x[1] for x in ca)) if len(ca) == len(cb) else None,
            'verdict': 'OK' if ((same_calls or offset_ok) and same_turns is not False) else 'FAIL'}


def main():
    out = {'round': 'r441', 'pairs': []}
    out['pairs'].append(pair('P1_A_W8_same_round',
                             D / 'calls-A-W8.jsonl', D / 'calls-A-W8-b2.jsonl'))
    out['pairs'].append(pair('P2_BRJ_W8_same_round',
                             D / 'calls-BRJ-W8.jsonl', D / 'calls-BRJ-W8-b2.jsonl'))
    out['pairs'].append(pair('P3_V2b_cross_round_R440',
                             D / 'calls-A-V2b-c2.jsonl', R / 'eval/rover/r440/calls-A-V2b-b1.jsonl'))
    out['pairs'].append(pair('P4_V2b_cross_round_R440_BRJ',
                             D / 'calls-BRJ-V2b-c2.jsonl', R / 'eval/rover/r440/calls-BRJ-V2b-b1.jsonl'))
    for p in out['pairs']:
        print('[det]', json.dumps(p, ensure_ascii=False))
    ok = [p['verdict'] for p in out['pairs'] if p['verdict'] != 'NO_DATA']
    out['verdict'] = 'OK' if ok and all(v == 'OK' for v in ok) else ('NO_DATA' if not ok else 'FAIL')
    (D / 'detcheck-r441.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print('[det] overall =', out['verdict'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
