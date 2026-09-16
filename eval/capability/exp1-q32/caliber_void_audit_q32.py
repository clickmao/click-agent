#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q32 · C4: 「分母两栏并列 ⇒ 旧口径作废/不可比声明」覆盖面审计 (AE.6 遗留)。

判据 (预注册 eval/capability/exp1-q32/prereg_q32.json §criteria.C4):
  · 面 = docs/reports/*.md + docs/plans/*.md 里的**数值对**行 (形如 `A → B` / `A ⇒ B` / `A vs B`);
  · 每处数值对必须在 ±3 行窗口内含显式声明词 (并列|双栏|两栏|不可比|口径变更|口径断点|作废|可比性);
  · 缺声明 ⇒ 分两档: 指标读数行 (含 口径|率|余量|tokens|降幅|条数|行数|分数|headroom) 判红;
    其他行记 NOTE (不判红) —— 词面启发式, 不是语义判定;
  · 判别力自证: has-decl 与 missing-decl 两侧样例必须被判成相反态; 空面 ⇒ 弃权 (rc=3)。
退出码: 0 无红 / 2 有红 / 3 环境失败。
"""
import json
import os
import re
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
OUT = 'eval/capability/exp1-q32/caliber_void_audit_q32.json'
PAIR_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(?:→|->|⇒|vs\.?|至)\s*(\d+(?:\.\d+)?)')
DECL = ('并列', '双栏', '两栏', '不可比', '口径变更', '口径断点', '作废', '可比性')
METRIC = ('口径', '率', '余量', 'tokens', 'token', '降幅', '条数', '行数', '分数', 'headroom',
          '份额', '保留率', '命中')
WINDOW = 3


CALIBER_MARK = ('口径', '两栏', '双栏', '不可比', '并列')
# v3 围栏词表 (strict 模式用): 补上文档里真实使用的「作废/取代/历史读数」表达 + 口径标签
# (负控族教训: 词表缺「不再作为当前/非口径」会把**已声明**的行判红 —— 标记出现 ≠ 未声明)
DECL_EXT = DECL + ('取代', '历史读数', '不再作为当前', '非口径', '不代表当前', '可比性断点',
                   '桩口径', '真值口径', '供应商真值', '旧段正文<br>', '参考档', '不并排')


def scan(path, strict=False):
    hits = []
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith('|') and '---' in ln:
            continue
        for m in PAIR_RE.finditer(ln):
            # strict 口径: 只认**该行自认是口径对**的并列 (含口径/两栏/双栏/不可比/并列标记)
            if strict and not any(k in ln for k in CALIBER_MARK):
                continue
            lo, hi = max(0, i - WINDOW), min(len(lines), i + WINDOW + 1)
            win = '\n'.join(lines[lo:hi])
            declared = any(d in win for d in (DECL_EXT if strict else DECL))
            metric = any(k in ln for k in METRIC)
            hits.append({'file': path, 'line': i + 1, 'pair': '%s→%s' % m.groups(),
                         'declared': declared, 'metric_line': metric,
                         'verdict': 'HAS_DECL' if declared else ('MISSING_DECL_metric' if metric else 'NOTE_missing_decl_nonmetric'),
                         'text': ln.strip()[:160]})
    return hits


def selftest():
    """判别力自证: 两侧样例 (has-decl / missing-decl) 必须判成相反态。"""
    import tempfile
    tmp = tempfile.mkdtemp(prefix='q32-caliber-')
    try:
        cases = [
            ('has_decl', '# x\n余量 2.258 → 2.019 (两栏并列, 旧口径只作参考)\n', False),
            ('missing_decl_metric', '# x\n余量 2.258 → 2.019\n', True),
            ('nonmetric_no_decl', '# x\n序号 1 → 2\n', False),
        ]
        bad = 0
        for name, body, want_missing in cases:
            p = os.path.join(tmp, name + '.md')
            open(p, 'w', encoding='utf-8').write(body)
            hits = scan(p)
            got = any(h['verdict'].startswith('MISSING_DECL') for h in hits)
            ok = got == want_missing
            bad += 0 if ok else 1
            print('  %-20s expect_missing=%s got=%s %s' % (name, want_missing, got, 'OK' if ok else 'FAIL'))
        print('SELFTEST %s (%d/3)' % ('PASS' if bad == 0 else 'FAIL', 3 - bad))
        return 0 if bad == 0 else 2
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if '--selftest' in sys.argv:
        return selftest()
    files = []
    for d in ('docs/reports', 'docs/plans'):
        for fn in sorted(os.listdir(os.path.join(ROOT, d))):
            if fn.endswith('.md'):
                files.append(os.path.join(d, fn))
    if not files:
        print('ENV_FAIL: 面为空 (docs/reports|docs/plans 无 .md) ⇒ 弃权')
        return 3
    strict = '--strict' in sys.argv
    out_id = OUT.replace('.json', '_strict.json') if strict else OUT
    all_hits, reds = [], []
    for f in files:
        all_hits.extend(scan(f, strict=strict))
    for h in all_hits:
        if h['verdict'].startswith('MISSING_DECL'):
            reds.append(h)
    by_file = {}
    for h in all_hits:
        by_file[h['file']] = by_file.get(h['file'], 0) + 1
    payload = {'round': 'EXP1-Q32', 'schema': 'caliber-void-audit/1', 'caliber': 'strict' if strict else 'v1_all_numeric_pairs',
 'decl_lexicon': list(DECL_EXT if strict else DECL),
               'face_files': len(files), 'n_pairs': len(all_hits),
               'n_declared': sum(1 for h in all_hits if h['declared']),
               'n_note_nonmetric': sum(1 for h in all_hits if h['verdict'].startswith('NOTE')),
               'n_red': len(reds), 'reds': reds, 'by_file': by_file, 'hits': all_hits,
               'caliber_note': '词面启发式 (±%d 行窗口 + 指标词表)%s; 非语义判定 ⇒ 红项须人工复核'
                               % (WINDOW, '; strict = 只认行内自认口径对' if strict else '')}
    with open(os.path.join(ROOT, out_id), 'w', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
    print('CALIBER=%s FACE_FILES=%d PAIRS=%d DECLARED=%d NOTE=%d RED=%d'
          % (payload['caliber'], len(files), len(all_hits), payload['n_declared'],
             payload['n_note_nonmetric'], len(reds)))
    for h in reds[:15]:
        print('  RED %s:%d %s | %s' % (h['file'], h['line'], h['pair'], h['text'][:90]))
    print('落盘 %s' % out_id)
    print('CALIBER_VOID=%s' % ('FAIL' if reds else 'OK'))
    return 2 if reds else 0


if __name__ == '__main__':
    sys.exit(main())
