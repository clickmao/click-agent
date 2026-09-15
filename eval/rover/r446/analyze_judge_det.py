#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R446 判官确定性探针分析器 (真机产品路径).

输入: 遥测 host.jsonl (correction_judge 事件) + 元数据
判据 (预注册见 docs/plans/v0.66.0-r446-*.md §3):
  D1 组内字母数: 1 ⇒ H2 (路径确定, 多态来自输入差异); >1 ⇒ H1 (路径非确定, 真缺陷)
  D2 前提核: local 行 prompt_len 必须恒定 (否则探针前提不成立 ⇒ INVALID_PREMISE, 非 PASS)
  D3 记账: tokens_evaluated >= prompt_new >= 0, 差值即 cache_n 逐行可见 (R443 铁律)
  D4 形态: 宿主日志出现 -np 1 (R430) 且 f32 KV (R407)
用法:
  python3 analyze_judge_det.py <telemetry.jsonl> <outdir> <ns> <bin_sha> [hostlog]
  python3 analyze_judge_det.py --selftest <outdir>     # 三态 fixture: 确定/非确定/缺文件
退出码: 0 = H2 确定 (或 selftest 全过); 2 = H1 非确定 / 缺文件 fail-closed; 3 = selftest 失配
"""
import json
import pathlib
import sys
from collections import Counter

EVENT_KEYS = ('point', 'event', 'name')
KV_KEYS = ('kv', 'fields', 'data')


def _rows_from(path):
    if not path.exists() or path.is_dir():
        raise SystemExit(f"FAIL-CLOSED: 遥测不可读: {path}")
    raw = path.read_text(encoding='utf-8-sig', errors='replace')
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith('{'):
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if not any(ev.get(k) == 'correction_judge' for k in EVENT_KEYS):
            continue
        kv = next((ev[k] for k in KV_KEYS if isinstance(ev.get(k), dict)), None)
        out.append(kv if kv is not None else ev)
    if not out:
        raise SystemExit(f"FAIL-CLOSED: 无 correction_judge 行: {path}")
    return out


def _int(d, key):
    v = d.get(key)
    if v is None or v == '':
        return -1
    try:
        return int(v)
    except Exception:
        return -1


def analyze(tele, outdir, sfx, bin_sha, hostlog=None):
    rows = _rows_from(pathlib.Path(tele))
    recs = [{
        'i': i + 1,
        'source': str(d.get('source', '')),
        'local_state': str(d.get('local_state', '')),
        'kind': str(d.get('kind', '')),
        'letter': str(d.get('letter', '')),
        'signal': str(d.get('signal', ''))[:32],
        'prompt_len': _int(d, 'prompt_len'),
        'ev': _int(d, 'tokens_evaluated'),
        'new': _int(d, 'prompt_new'),
        'gen': _int(d, 'gen_tokens'),
        'ms': _int(d, 'ms'),
        'msg_head': str(d.get('msg_head', '')),
    } for i, d in enumerate(rows)]
    local = [r for r in recs if r['source'] == 'local']
    letters = Counter(r['letter'] for r in local)
    plens = Counter(r['prompt_len'] for r in local)
    caches = Counter(r['ev'] - r['new'] for r in local if r['ev'] >= 0 and r['new'] >= 0)

    form_ok, form_ev = None, ''
    if hostlog:
        hp = pathlib.Path(hostlog)
        if hp.exists():
            txt = hp.read_text(encoding='utf-8', errors='replace')
            form_ok = ('-np 1' in txt or '"-np", "1"' in txt) and 'f32' in txt
            seg = [ln for ln in txt.splitlines() if '-np' in ln or 'cache-type-k' in ln][:3]
            form_ev = ' | '.join(seg)[:300]
        else:
            form_ok = False
            form_ev = f'hostlog 缺失: {hp}'

    crit = {
        'D1_deterministic': {'pass': len(letters) == 1, 'value': dict(letters), 'n_local': len(local)},
        'D2_inputs_identical': {'pass': len(plens) == 1 and len(local) >= 8, 'value': dict(plens)},
        'D3_accounting': {'pass': bool(local) and all(r['ev'] >= r['new'] >= 0 for r in local),
                          'value': f"ev-new 分布={dict(caches)}"},
        'D4_form': {'pass': bool(form_ok), 'value': form_ev or 'no-hostlog'},
    }
    if not crit['D2_inputs_identical']['pass']:
        concl = 'INVALID_PREMISE'
    elif crit['D1_deterministic']['pass']:
        concl = 'H2_DETERMINISTIC'
    else:
        concl = 'H1_NONDETERMINISTIC'
    doc = {'round': 'R446', 'instrument': 'judge_determinism_probe', 'ns': sfx, 'bin_sha256': bin_sha,
           'judge_rows_total': len(recs), 'local_rows': len(local),
           'source_hist': dict(Counter(r['source'] for r in recs)),
           'local_state_hist': dict(Counter(r['local_state'] for r in local)),
           'rows': recs, 'criteria': crit, 'conclusion': concl}
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    label = sys.argv[6] if len(sys.argv) > 6 else 'JDET'
    for name in (f'verdict-{label}{sfx}.json', f'probe-judge-det{label}{sfx}.json'):
        (outdir / name).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f"判官行 {len(recs)} (local {len(local)})  source={doc['source_hist']}")
    print(f"letter 分布: {dict(letters)}   prompt_len: {dict(plens)}   ev-new: {dict(caches)}")
    for r in recs:
        print(f"  #{r['i']:2d} {r['source']:9s} {r['local_state'][:20]:20s} kind={r['kind']:8s} "
              f"letter={r['letter']!r:6s} plen={r['prompt_len']:4d} ev={r['ev']:4d} new={r['new']:4d} "
              f"gen={r['gen']:3d} {r['ms']:7d}ms sig={r['signal']}")
    for k, v in crit.items():
        print(('  PASS ' if v['pass'] else '  FAIL ') + k, v)
    print('结论:', concl)
    return 0 if concl == 'H2_DETERMINISTIC' else 2


def _selftest(outdir):
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='r446-selftest-'))

    def w(name, letters, plens):
        p = tmp / name
        with p.open('w', encoding='utf-8') as fh:
            for L, pl in zip(letters, plens):
                fh.write(json.dumps({'event': 'correction_judge', 'source': 'local', 'local_state': 'answered',
                                     'kind': 'Adopt' if L == 'A' else 'Neutral', 'letter': L, 'signal': 'llm',
                                     'prompt_len': pl, 'tokens_evaluated': 120, 'prompt_new': 100, 'gen_tokens': 20,
                                     'ms': 900, 'msg_head': '好，按这个来。'}, ensure_ascii=False) + '\n')
        return p
    cases = [(w('det.jsonl', ['A'] * 10, [213] * 10), 0, 'H2_DETERMINISTIC', 'det'),
             (w('nondet.jsonl', ['A', 'C', 'N'] * 3, [213] * 9), 2, 'H1_NONDETERMINISTIC', 'nondet'),
             (w('premise.jsonl', ['A', 'C'], [213, 240]), 2, 'INVALID_PREMISE', 'premise'),
             (tmp / 'missing.jsonl', 2, '', 'missing')]
    ok = True
    for path, exp_rc, exp_tag, label in cases:
        try:
            rc = analyze(path, outdir, '-st', 'deadbeef')
        except SystemExit as e:
            rc = 2
            print(f'  selftest {label:8s} fail-closed: {e}')
        tag = ''
        vp = pathlib.Path(outdir) / 'verdict-JDET-st.json'
        if vp.exists():
            tag = json.loads(vp.read_text(encoding='utf-8')).get('conclusion', '')
            vp.unlink()
        good = (rc == exp_rc) and (exp_tag in tag or exp_tag == '')
        ok = ok and good
        print(f"  selftest {label:8s} rc={rc} 期望rc={exp_rc} 结论={tag or '-'} {'OK' if good else 'MISMATCH'}")
    print(f"[selftest] {'ALL OK' if ok else 'FAILED'}")
    return 0 if ok else 3


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == '--selftest':
        return _selftest(argv[1] if len(argv) > 1 else '.')
    if len(argv) < 4:
        raise SystemExit('用法: analyze_judge_det.py <telemetry> <outdir> <ns> <bin_sha> [hostlog] | --selftest <outdir>')
    return analyze(argv[0], argv[1], argv[2], argv[3], argv[4] if len(argv) > 4 else None)


if __name__ == '__main__':
    sys.exit(main())
