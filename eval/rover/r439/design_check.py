#!/usr/bin/env python3
"""R439 设计审计器 — 用**权威源**（src/agent.modelqueue/LocalGenerationPort.cs）派生的机械过滤表，
独立（Python 第二实现）判定每个网格逐轮的**结构类别**，并与历史实测的 per_turn_actual 比对自证。

用途:
  (a) 自证: 对 p8/p12 预测标签 == R436/R438 实测标签（工具可信度）
  (b) 对 V20 给出「结构上**不可能**被跳」的轮集合（白名单性质: 只有 AckFamily 轮才可能 Skip）
铁律: 常量**一律从 C# 源程序化提取**（禁手打；历史教训: U+200B 混入 ⇒ 假阳性）。
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
SRC = ROOT / 'src/agent.modelqueue/LocalGenerationPort.cs'
OUT = ROOT / 'eval/rover/r439'


def extract_list(name: str, text: str) -> list[str]:
    m = re.search(rf'string\[\]\s+{name}\s*=\s*\{{(.*?)\}};', text, re.S)
    if not m:
        raise SystemExit(f'[致命] 未找到 {name}')
    return re.findall(r'"([^"]*)"', m.group(1))


def extract_const(name: str, text: str) -> str:
    m = re.search(rf'const\s+(?:string|int)\s+{name}\s*=\s*([^;]+);', text)
    if not m:
        raise SystemExit(f'[致命] 未找到 {name}')
    return m.group(1).strip().strip('"')


def main() -> int:
    src = SRC.read_text(encoding='utf-8')
    q = extract_list('QuestionSignals', src)
    r = extract_list('RequestSignals', src)
    c = extract_list('CorrectionSignals', src)
    ack_chars = extract_const('AckFamilyChars', src)
    thr = int(extract_const('SubstantiveLengthThreshold', src))
    # 源内断言: 字符集不得含 Unicode 空白/零宽 (历史事故)
    assert not any(ch.isspace() or ord(ch) in (0x200B, 0xFEFF, 0x200C, 0x200D) for ch in ack_chars), 'AckFamilyChars 含空白/零宽'
    facts = {
        'source': str(SRC.relative_to(ROOT)),
        'QuestionSignals': q, 'RequestSignals': r, 'CorrectionSignals': c,
        'AckFamilyChars': ack_chars, 'SubstantiveLengthThreshold': thr,
        'AckFamilyChars_len': len(ack_chars),
    }

    def mech_pass(m: str) -> tuple[bool, str]:
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

    def mech_ack(m: str) -> bool:
        t = m.strip()
        if not t:
            return False
        n = 0
        for ch in t:
            if ch.isspace() or _is_cjk_punct(ch):
                continue
            if ch not in ack_chars:
                return False
            n += 1
            if n > 10:
                return False
        return n > 0

    def _is_cjk_punct(ch: str) -> bool:
        return ch in '，。！、；：""''（）《》—…·,.!?;:()[]{}'

    grids = {}
    for g, path in (('p8', OUT / 'grid/task-p8.json'), ('p12', ROOT / 'eval/rover/r438/grid/task-p12.json'),
                    ('V20', OUT / 'grid/task-V20.json')):
        grids[g] = json.loads(path.read_text(encoding='utf-8'))['turns']

    # 历史实测标签（工具自证: 预测应逐轮相同）
    measured = {}
    def _find_pta(obj):
        if isinstance(obj, dict):
            for key in ('per_turn', 'per_turn_actual'):
                if isinstance(obj.get(key), list) and obj[key] and isinstance(obj[key][0], dict):
                    return [{'turn': r.get('turn'), 'actual': r.get('actual'), 'want': r.get('want'),
                             'family': r.get('family'), 'mech': r.get('mech')} for r in obj[key]]
            for v in obj.values():
                got = _find_pta(v)
                if got is not None:
                    return got
        elif isinstance(obj, list):
            for v in obj:
                got = _find_pta(v)
                if got is not None:
                    return got
        return None

    for arm, path in (('p8', ROOT / 'eval/rover/r436/verdict-BRJ-p8.json'),
                      ('p12', ROOT / 'eval/rover/r438/verdict-BRJ-p12.json')):
        if path.exists():
            v = json.loads(path.read_text(encoding='utf-8'))
            pta = _find_pta(v)
            if pta:
                measured[arm] = pta
    if len(measured) != 2:
        raise SystemExit(f'[致命] 自证基准缺失: {sorted(measured)}')

    report = {'facts': facts, 'grids': {}, 'selftest': {}}
    for g, turns in grids.items():
        rows = []
        for i, t in enumerate(turns, 1):
            mp, why = mech_pass(t)
            ack = mech_ack(t)
            if mp:
                cls = 'pass:mechanical'
            elif ack:
                cls = 'skip-eligible(ack):r1决定'
            else:
                cls = 'pass:residual-band(结构上不可能Skip)'
            rows.append({'turn': i, 'text': t, 'mechanical_pass': mp, 'why': why,
                         'ack_family': ack, 'class': cls})
        report['grids'][g] = rows

    # 工具自证: p8/p12 预测标签 vs 实测标签
    for g, m in measured.items():
        rows = report['grids'][g]
        by_turn = {r_['turn']: r_ for r_ in rows}
        pred, actual, want, fam, mech = [], [], [], [], []
        for rec in m:
            t = rec['turn']
            r_ = by_turn.get(t)
            if r_ is None:
                continue
            pred.append('pass' if (r_['mechanical_pass'] or not r_['ack_family']) else 'skip-or-pass')
            actual.append(rec['actual'])
            want.append(rec['want'])
            fam.append(rec['family'])
            mech.append(bool(rec['mech']))
        pred_mech = [by_turn[rec['turn']]['mechanical_pass'] for rec in m if rec['turn'] in by_turn]
        dev = [(i + 1, p, a) for i, (p, a) in enumerate(zip(pred, actual)) if a == 'skip' and p == 'pass']
        report['selftest'][g] = {
            'pred': pred, 'actual': actual, 'want': want, 'family': fam,
            'pred_mech': pred_mech, 'verdict_mech': mech,
            'mech_match': pred_mech == mech,
            'ack_family_match': [(by_turn[rec['turn']]['ack_family'], rec['family']) for rec in m if rec['turn'] in by_turn],
            'violations_skip_without_ack': dev,
            'n_violations': len(dev),
            'n_measured': len(m),
            'skips': sum(1 for x in actual if x == 'skip'),
            'want_mismatch': [rec['turn'] for rec in m if rec['turn'] in by_turn and rec['want'] != rec['actual']],
        }

    v20 = report['grids']['V20']
    report['V20_summary'] = {
        'skips_possible': [r_['turn'] for r_ in v20 if r_['ack_family'] and not r_['mechanical_pass']],
        'structurally_never_skip': [r_['turn'] for r_ in v20 if not r_['ack_family']],
        'skip_eligible_ratio': round(sum(1 for r_ in v20 if r_['ack_family']) / len(v20), 4),
        'mechanical_pass_turns': [r_['turn'] for r_ in v20 if r_['mechanical_pass']],
    }
    (OUT / 'design-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f"[facts] ack_chars={len(ack_chars)}字 thr={thr} Q/R/C={len(q)}/{len(r)}/{len(c)}")
    for g in report['grids']:
        st = report['selftest'].get(g)
        if st:
            print(f"[grid {g}] n={len(report['grids'][g])} 自证: 实测轮={st['n_measured']} 实测skip={st['skips']} "
                  f"机械表一致={st['mech_match']} 违例(skip而无ack族)={st['n_violations']} want≠actual={st['want_mismatch']}")
        else:
            n = len(report['grids'][g])
            nack = sum(1 for x in report['grids'][g] if x['ack_family'])
            print(f"[grid {g}] n={n} ack族轮={nack} (无实测基准)")
    print('[V20] 结构可跳轮 =', report['V20_summary']['skips_possible'],
          f"(占比 {report['V20_summary']['skip_eligible_ratio']:.2%})")
    print('[V20] 结构上永不可跳 =', report['V20_summary']['structurally_never_skip'])
    print('[V20] 机械 Pass 轮 =', report['V20_summary']['mechanical_pass_turns'])
    print('[written]', OUT / 'design-audit.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
