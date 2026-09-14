#!/usr/bin/env python3
"""R440 设计审计器 — 机械过滤/认可族表**一律由 C# 权威源程序化派生**（禁手打; 历史事故: U+200B 假阳性）。

用途:
  (a) 工具自证: 对 p8/p12 的预测标签必须逐轮 == 历史实测标签（否则仪器不可信, fail-closed）
  (b) 对 V1/V2/V4/V5 做**跑前设计断言**:
      D1 每个 want=pass 且 mech!=true 的轮 **非机械 Pass**（真由 r1 门判）
      D2 每个 want=pass 的轮 **不在认可族**（白名单性质: 只有认可族轮才可能被 Skip ⇒ 结构上不可误杀）
      D3 每个 want=skip 的轮 **必须在认可族**（否则设计自相矛盾）
      D4 V5 全网格 0 个认可族轮; V4 认可族轮全在 t14..t20
      D5 残余带轮集与 r1_positions 声明一致
输出 eval/rover/r440/design-audit.json; 任一断言失败 ⇒ exit 2。
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
SRC = ROOT / 'src/agent.modelqueue/LocalGenerationPort.cs'
OUT = ROOT / 'eval/rover/r440'


def extract_list(name, text):
    m = re.search(rf'string\[\]\s+{name}\s*=\s*\{{(.*?)\}};', text, re.S)
    if not m:
        raise SystemExit(f'[致命] 未找到 {name}')
    return re.findall(r'"([^"]*)"', m.group(1))


def extract_const(name, text):
    m = re.search(rf'const\s+(?:string|int)\s+{name}\s*=\s*([^;]+);', text)
    if not m:
        raise SystemExit(f'[致命] 未找到 {name}')
    return m.group(1).strip().strip('"')


PUNCT = '，。！、；：""\'\'（）《》—…·,.!?;:()[]{}'


def main():
    src = SRC.read_text(encoding='utf-8')
    q, r, c = extract_list('QuestionSignals', src), extract_list('RequestSignals', src), extract_list('CorrectionSignals', src)
    ack_chars = extract_const('AckFamilyChars', src)
    thr = int(extract_const('SubstantiveLengthThreshold', src))
    assert not any(ch.isspace() or ord(ch) in (0x200B, 0xFEFF, 0x200C, 0x200D) for ch in ack_chars), 'AckFamilyChars 含空白/零宽'
    facts = {'source': str(SRC.relative_to(ROOT)), 'QuestionSignals_n': len(q), 'RequestSignals_n': len(r),
             'CorrectionSignals_n': len(c), 'AckFamilyChars_len': len(ack_chars), 'SubstantiveLengthThreshold': thr}

    def mech_pass(m):
        if not m.strip():
            return True, 'empty'
        if any(ch in m for ch in '?？'):
            return True, 'qmark'
        for w in q:
            if w in m:
                return True, f'question:{w}'
        for w in r:
            if w in m:
                return True, f'request:{w}'
        for w in c:
            if w in m:
                return True, f'correction:{w}'
        if any(ch in m for ch in '`/\\'):
            return True, 'pathish'
        if any(ch.isdigit() for ch in m):
            return True, 'digit'
        if len(m) >= thr:
            return True, f'length>={thr}'
        return False, 'residual-band'

    def mech_ack(m):
        t = m.strip()
        if not t:
            return False
        n = 0
        for ch in t:
            if ch.isspace() or ch in PUNCT:
                continue
            if ch not in ack_chars:
                return False
            n += 1
            if n > 10:
                return False
        return n > 0

    grids = {}
    for g in ('p8', 'p12', 'V20', 'V1', 'V2', 'V4', 'V5'):
        for base in (OUT / 'grid', ROOT / 'eval/rover/r436/grid', ROOT / 'eval/rover/r438/grid', ROOT / 'eval/rover/r439/grid'):
            f = base / f'task-{g}.json'
            if f.exists():
                grids[g] = json.load(open(f, encoding='utf-8'))
                break

    report = {'facts': facts, 'grids': {}, 'self_proof': {}, 'design_assertions': {}}
    for g, spec in grids.items():
        rows = []
        for i, t in enumerate(spec['turns'], 1):
            mp, why = mech_pass(t)
            ack = mech_ack(t)
            cls = 'pass:mechanical' if mp else ('skip-eligible(ack):r1决定' if ack else 'pass:residual-band(结构上不可能Skip)')
            rows.append({'turn': i, 'text': t, 'mechanical_pass': mp, 'why': why, 'ack_family': ack, 'class': cls})
        report['grids'][g] = rows

    # 自证: p8/p12 预测 vs 实测（历史 verdict 的 per_turn）
    def find_pta(obj):
        if isinstance(obj, dict):
            for key in ('per_turn', 'per_turn_actual'):
                if isinstance(obj.get(key), list) and obj[key] and isinstance(obj[key][0], dict):
                    return obj[key]
            for v in obj.values():
                got = find_pta(v)
                if got is not None:
                    return got
        elif isinstance(obj, list):
            for v in obj:
                got = find_pta(v)
                if got is not None:
                    return got
        return None

    for g, p in (('p8', ROOT / 'eval/rover/r436/verdict-BRJ-p8.json'), ('p12', ROOT / 'eval/rover/r438/verdict-BRJ-p12.json')):
        if not p.exists() or g not in report['grids']:
            continue
        pta = find_pta(json.load(open(p, encoding='utf-8')))
        by_turn = {x['turn']: x for x in report['grids'][g]}
        mism, n = [], 0
        for rec in pta:
            t = rec['turn']
            if t not in by_turn or rec.get('want') is None or rec.get('consumed_as_ask_answer'):
                continue
            n += 1
            pred_skip_possible = by_turn[t]['mechanical_pass'] is False and by_turn[t]['ack_family'] is True
            ok = (rec['want'] == 'skip') == pred_skip_possible
            if not ok:
                mism.append({'turn': t, 'want': rec['want'], 'actual': rec.get('actual'), 'pred': by_turn[t]['class']})
        report['self_proof'][g] = {'compared': n, 'mismatch': mism, 'verdict': 'OK' if not mism else 'MISMATCH'}

    # 跑前设计断言
    for g in ('V1', 'V2', 'V4', 'V5'):
        if g not in grids:
            continue
        spec, rows = grids[g], report['grids'][g]
        exp = {int(e['turn']): e for e in spec.get('expected', [])}
        d0 = sorted(exp) == list(range(1, len(rows) + 1)) and len(exp) == len(rows)
        d1 = [x['turn'] for x in rows if exp.get(x['turn'], {}).get('want') == 'pass' and exp.get(x['turn'], {}).get('mech') is not True and x['mechanical_pass']]
        d2 = [x['turn'] for x in rows if exp.get(x['turn'], {}).get('want') == 'pass' and x['ack_family']]
        d3 = [x['turn'] for x in rows if exp.get(x['turn'], {}).get('want') == 'skip' and not x['ack_family']]
        ack_turns = [x['turn'] for x in rows if x['ack_family']]
        d4 = None
        if g == 'V5':
            d4 = ack_turns == []
        elif g == 'V4':
            d4 = all(t >= 14 for t in ack_turns) and len(ack_turns) == 7
        d5 = sorted(x['turn'] for x in rows if not x['mechanical_pass']) == sorted(spec.get('r1_positions', []))
        report['design_assertions'][g] = {
            'D0_expected_covers_turns_1_N': d0,
            'D1_want_pass_not_mechanical_violations': d1, 'D2_want_pass_in_ack_family_violations': d2,
            'D3_want_skip_not_ack_violations': d3, 'D4_position_ok': d4, 'D5_residual_set_match': d5,
            'ack_turns': ack_turns, 'N': len(rows),
            'verdict': 'OK' if (d0 and not d1 and not d2 and not d3 and d4 is not False and d5) else 'FAIL'}

    bad_self = [g for g, v in report['self_proof'].items() if v['verdict'] != 'OK']
    bad_design = [g for g, v in report['design_assertions'].items() if v['verdict'] != 'OK']
    report['verdict'] = 'OK' if (not bad_self and not bad_design and len(report['self_proof']) == 2) else 'FAIL'
    json.dump(report, open(OUT / 'design-audit.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    for g, v in report['self_proof'].items():
        print(f'[self-proof] {g}: compared={v["compared"]} {v["verdict"]}')
    for g, v in report['design_assertions'].items():
        print(f'[design] {g}: N={v["N"]} ok={v["verdict"]} D0={v["D0_expected_covers_turns_1_N"]} ack_turns={v["ack_turns"]} '
              f'D1={len(v["D1_want_pass_not_mechanical_violations"])} D2={len(v["D2_want_pass_in_ack_family_violations"])} '
              f'D3={len(v["D3_want_skip_not_ack_violations"])} D4={v["D4_position_ok"]} D5={v["D5_residual_set_match"]}')
    print('[verdict]', report['verdict'], '| wrote', OUT / 'design-audit.json')
    return 0 if report['verdict'] == 'OK' else 2


if __name__ == '__main__':
    sys.exit(main())
