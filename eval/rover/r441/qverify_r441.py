#!/usr/bin/env python3
"""R441 质量不退化校验器（C6 的证据来源，确定性、无 LLM 评分）。

判据（全部机械）:
  Q1 非跳轮**逐位同值**: BRJ 臂第 i 轮 reply == A 臂第 i 轮 reply（i ∉ S）⇒ 「门/r1 判官不改变未跳轮的用户可见输出」
  Q2 跳轮回复 = **本地消化族**文本，且与权威源逐位相同（禁手打: 从 C# 常量程序化派生）
  Q3 无空回复（两臂全部轮次）
  Q4 跳过轮回复 != A 臂同轮回复（证明跳轮确实走了本地路径, 不是静默回放远端）
输出 eval/rover/r441/qverify-r441.json；exit 0 全绿。
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
D = ROOT / 'eval/rover/r441'
CS = ROOT / 'src/agent.modelqueue/ModelQueueRouter.cs'
INVISIBLE = set('\u200b\u200c\u200d\ufeff\u00a0\u0001')
GRIDS = ('W8', 'W20', 'M20', 'V2b')


def derive_local_skip() -> dict:
    src = CS.read_text(encoding='utf-8')
    m = re.search(r'public const string LocalSkipFallback\s*=\s*"((?:[^"\\]|\\.)*)"\s*;', src)
    assert m, 'Q0 失败: 未在权威源找到 LocalSkipFallback 常量'
    raw = m.group(1)
    lit = re.sub(r'\\u([0-9a-fA-F]{4})', lambda x: chr(int(x.group(1), 16)), raw)
    lit = lit.replace('\\"', '"').replace('\\\\', '\\').replace('\\n', '\n')
    assert not (INVISIBLE & set(lit)), 'Q0 失败: 常量含不可见码位'
    assert len(lit) >= 8 and lit.endswith('。'), f'Q0 失败: 常量形状异常 {lit!r}'
    return {'const_name': 'ModelQueueRouter.LocalSkipFallback', 'source': str(CS.relative_to(ROOT)),
            'value': lit, 'length': len(lit)}


def turns(p):
    p = pathlib.Path(p)
    if not p.exists():
        return None
    return json.load(open(p, encoding='utf-8'))['turns']


def main():
    ls = derive_local_skip()
    vb_all = {}
    for g in GRIDS:
        for sfx in ('', '-c2', '-b2'):
            for arm in ('A', 'BRJ'):
                p = D / f'verdict-{arm}-{g}{sfx}.json'
                if p.exists() and (g, arm) not in vb_all:
                    vb_all[(g, arm)] = json.load(open(p, encoding='utf-8'))
    out = {'local_skip_fallback': ls, 'grids': {}}
    for g in GRIDS:
        va, vb = vb_all.get((g, 'A')), vb_all.get((g, 'BRJ'))
        for sfx in ('', '-c2', '-b2'):
            if (D / f'turns-A-{g}{sfx}.jsonl').exists():
                break
        ta, tb = turns(D / f'turns-A-{g}{sfx}.jsonl'), turns(D / f'turns-BRJ-{g}{sfx}.jsonl')
        if not (va and vb and ta and tb):
            out['grids'][g] = 'NO_DATA'
            continue
        sk = sorted(t for t, r in {r['turn']: r for r in vb['per_turn']}.items() if r.get('actual') == 'skip')
        ra = {r['turn']: str(r.get('reply') or '') for r in ta}
        rb = {r['turn']: str(r.get('reply') or '') for r in tb}
        nonskip = [t for t in sorted(rb) if t not in sk]
        q1_bad = [t for t in nonskip if ra.get(t) != rb.get(t)]
        q2_bad = [t for t in sk if rb.get(t) != ls['value']]
        q3_bad = [t for t in sorted(rb) if not str(rb.get(t) or '').strip()] + [t for t in sorted(ra) if not str(ra.get(t) or '').strip()]
        q4_bad = [t for t in sk if rb.get(t) == ra.get(t)]
        ok = not (q1_bad or q2_bad or q3_bad or q4_bad)
        out['grids'][g] = {'skips': sk, 'nonskip_turns': len(nonskip),
                           'Q1_nonskip_identical': len(nonskip) - len(q1_bad), 'Q1_bad': q1_bad,
                           'Q2_skip_is_local_family': len(sk) - len(q2_bad), 'Q2_bad': q2_bad,
                           'Q3_empty': q3_bad, 'Q4_skip_differs_from_A_bad': q4_bad,
                           'verdict': 'OK' if ok else 'FAIL'}
    subs = [v['verdict'] for v in out['grids'].values() if isinstance(v, dict)]
    out['verdicts'] = {'C6': 'OK' if subs and all(v == 'OK' for v in subs) else ('NO_DATA' if not subs else 'FAIL')}
    json.dump(out, open(D / 'qverify-r441.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('[Q0] local_skip_fallback 派生自', ls['source'], 'len =', ls['length'])
    for g, v in out['grids'].items():
        print(f'[{g}]', json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v)
    print('[C6]', out['verdicts']['C6'], '| wrote', D / 'qverify-r441.json')
    return 0 if out['verdicts']['C6'] == 'OK' else 2


if __name__ == '__main__':
    sys.exit(main())
