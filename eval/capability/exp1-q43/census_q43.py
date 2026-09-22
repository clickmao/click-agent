#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q43 · 只读普查件 (候选#1 序列化形态统一收益 / 候选#5 尾 LF 写入器缺口)。

零写入被测面(除自身产物) / 零重测 / 零远端。判据见 prereg_q43.json 的 M3 / M4。

候选#1 (M3): 找出所有硬编码 `indent=1` 的 .py, 按**是否被活通路引用**分类:
  活通路 = 被 tools/** · scripts/** · eval/capability/*.py(顶层工具) · eval/rover/*.py 引用;
  一次性件 = 只被自身轮次目录 / eval/archive/** 引用。
  M3 判据: 活通路件数 == 0 ⇒ 形态统一零功能增益 ⇒ 收窄关闭。

候选#5 (M4): 自 R481(尾契约闸入册)起的**新增**产物件(.json/.jsonl)里缺尾 LF 的数量。
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]     # repo root
OUT = ROOT / 'eval/capability/exp1-q43/census_q43.json'
LIVE_PREFIXES = ('tools/', 'scripts/', 'src/')
SKIP_DIRS = ('__pycache__', '.git', 'node_modules', 'artifacts', 'bin', 'obj')
ROUND_RE = re.compile(r'^(?:eval/(?:capability|rover|archive)/[^/]+|docs/|data/)')


def git(*a):
    return subprocess.run(['git', '-C', str(ROOT)] + list(a), capture_output=True, text=True)


def py_files():
    for p in ROOT.rglob('*.py'):
        s = str(p.relative_to(ROOT))
        if any(d in s for d in SKIP_DIRS):
            continue
        yield s


def refs_of(basename, exclude):
    """在仓内文本文件里搜 basename 引用 (git grep, 避免自引用)。"""
    r = git('grep', '-l', '-F', basename, '--', '*.py', '*.sh', '*.md', '*.json', '*.jsonl')
    out = []
    for ln in (r.stdout or '').splitlines():
        ln = ln.strip()
        if not ln or ln == exclude:
            continue
        out.append(ln)
    return out


def census_c1():
    files = []
    for rel in py_files():
        try:
            txt = (ROOT / rel).read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        if re.search(r'indent\s*=\s*1\b', txt):
            files.append(rel)
    live, once = [], []
    for rel in files:
        r = refs_of(pathlib.Path(rel).name, rel)
        is_live = any(x.startswith(LIVE_PREFIXES) for x in r)
        (live if is_live else once).append({'file': rel, 'refs': r[:6], 'n_refs': len(r)})
    return {'total_with_indent1': len(files), 'live_path': live, 'executed_once': once,
            'live_count': len(live), 'once_count': len(once)}


def r481_commit():
    for pat in ('R481', 'r481', 'tail-lf', 'tail_lf', 'R481-tail-lf'):
        r = git('log', '--all', '--format=%H %s', '-S', pat, '-n', '1')
        if (r.stdout or '').strip():
            return (r.stdout or '').strip().splitlines()[0]
    r = git('log', '--all', '--format=%H %s', '--grep=R481', '-n', '1')
    return (r.stdout or '').strip().splitlines()[0] if (r.stdout or '').strip() else None


def census_c5():
    sha = r481_commit()
    if not sha:
        return {'env': 'R481 提交不可得 ⇒ 弃权', 'sha': None}
    sha = sha.split()[0]
    r = git('diff', '--name-only', '--diff-filter=A', '%s..HEAD' % sha)
    added = [x.strip() for x in (r.stdout or '').splitlines() if x.strip()]
    art = [p for p in added if p.endswith(('.json', '.jsonl'))]
    missing = []
    checked = 0
    for rel in art:
        p = ROOT / rel
        if not p.exists():
            continue
        checked += 1
        b = p.read_bytes()
        if b and not b.endswith(b'\n'):
            missing.append(rel)
    return {'r481_sha': sha, 'added_total': len(added), 'added_json_like': len(art),
            'checked_on_disk': checked, 'missing_trailing_lf': len(missing),
            'missing_sample': missing[:20],
            'note': '缺尾 LF 的**新产物**件(自 R481 起新增) —— 反映写入器缺口是否仍在产'}


def main():
    c1 = census_c1()
    c5 = census_c5()
    payload = {'round': 'EXP1-Q43', 'schema': 'census-q43/1',
               'c1_form_unification': c1, 'c5_tail_lf': c5,
               'm3_verdict': ('RE-FRAME ZERO GAIN' if c1['live_count'] == 0 else 'KEEP (活通路存在)'),
               'm4_verdict': ('CLOSED (新增缺尾 LF = 0)' if c5.get('missing_trailing_lf') == 0
                              else 'CARRY-OVER (新增缺尾 LF = %s)' % c5.get('missing_trailing_lf'))}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    back = json.loads(OUT.read_text(encoding='utf-8'))
    print('READBACK=%s' % ('OK' if back == payload else 'FAIL'))
    print('C1 total_indent1=%d live=%d once=%d' % (c1['total_with_indent1'], c1['live_count'], c1['once_count']))
    for x in c1['live_path']:
        print('  LIVE %s <- %s' % (x['file'], x['refs'][:2]))
    print('C5 r481=%s added_json_like=%s checked=%s missing_lf=%s'
          % (c5.get('r481_sha'), c5.get('added_json_like'), c5.get('checked_on_disk'), c5.get('missing_trailing_lf')))
    for f in c5.get('missing_sample', [])[:8]:
        print('  MISSING_LF %s' % f)
    print('M3=%s M4=%s out=%s' % (payload['m3_verdict'], payload['m4_verdict'], OUT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
