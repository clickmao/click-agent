#!/usr/bin/env python3
# R474: 把 docs/reports/iteration-master-plan.md 的「轮次索引」从 R441–R458 扩展到 R441–R472。
# 机取自 docs/verification-registry.json (勿手改块) — 只追加行 + 改 2 处标题/自检行, 其余逐字节保留。
import collections, io, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REG = os.path.join(ROOT, 'docs', 'verification-registry.json')
MP = os.path.join(ROOT, 'docs', 'reports', 'iteration-master-plan.md')
FROM, TO = 459, 474

reg = json.load(io.open(REG, encoding='utf-8'), object_pairs_hook=collections.OrderedDict)
rows = reg['rows']


def rnum(r):
    try:
        return int(str(r.get('owner_round', '')).lstrip('Rr'))
    except Exception:
        return None


sel = [r for r in rows if rnum(r) is not None and FROM <= rnum(r) <= TO]
sel.sort(key=lambda r: (rnum(r), r['id']))
new_lines = []
for r in sel:
    cap = str(r.get('capability', '')).replace('\n', ' ').replace('|', '/')
    if len(cap) > 88:
        cap = cap[:88] + '…'
    new_lines.append('| R%d | `%s` | %s | %s |\n' % (rnum(r), r['id'], r.get('level', '?'), cap))

lines = io.open(MP, encoding='utf-8').read().splitlines(keepends=True)
i_cov = next(i for i, l in enumerate(lines) if l.startswith('覆盖自检:'))
i_hdr = next(i for i, l in enumerate(lines) if l.startswith('## R441–R458 轮次索引') or l.startswith('## R441–R472 轮次索引') or l.startswith('## R441–R474 轮次索引'))
# 幂等: 表内已存在的 id 不再插入
present = set(re.findall(r'\|\s*R\d+\s*\|\s*`([^`]+)`\s*\|', ''.join(lines[i_hdr:i_cov])))
new_lines = [l for l in new_lines if re.findall(r'`([^`]+)`', l)[0] not in present]

covered = sorted({rnum(r) for r in rows if rnum(r) is not None and 441 <= rnum(r) <= TO})
missing = [n for n in range(441, TO + 1) if n not in covered]
imp = io.open(os.path.join(ROOT, 'docs', 'improvements.md'), encoding='utf-8').read()
missing_txt = ''
if missing:
    with_block = [n for n in missing if ('\n## R%d（' % n) in imp]
    unused = [n for n in missing if n not in with_block]
    parts = []
    if with_block:
        parts.append('有块但无登记行: %s' % ', '.join(str(n) for n in with_block))
    if unused:
        parts.append('**该号未被使用(improvements.md 亦无块): %s**' % ', '.join(str(n) for n in unused))
    missing_txt = '**缺登记行轮号: %s**（%s）。' % (', '.join(str(n) for n in missing), '；'.join(parts))
new_cov = ('覆盖自检: 轮号 [%s]；registry rows=%d，updated_round=%s。%s\n'
           % (', '.join(str(n) for n in covered), len(rows), reg.get('updated_round', '?'), missing_txt))
new_hdr = lines[i_hdr]
if True:
    import re as _re
    new_hdr = _re.sub(r'^## R441–R4\d\d 轮次索引（[^；]*；',
                      '## R441–R474 轮次索引（2026-09-15 首次回填，R474 扩展到 R474；', lines[i_hdr])
assert new_cov != lines[i_cov]
out = lines[:i_cov] + new_lines + [new_cov] + lines[i_cov + 1:]
out[i_hdr] = new_hdr
io.open(MP, 'w', encoding='utf-8', newline='\n').write(''.join(out))
print(json.dumps({'rows_added': len(new_lines), 'rounds': [rnum(r) for r in sel],
                  'registry_rows': len(rows), 'updated_round': reg.get('updated_round'),
                  'file_lines': len(out)}, ensure_ascii=False))
print(new_cov.strip())
