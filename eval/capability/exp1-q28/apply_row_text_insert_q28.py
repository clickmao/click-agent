#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q28 · 登记行**文本插入**改写器 (R409 纪律的 fallback 分支).

背景 (本轮实测, 有外部真值):
  `bind_evidence.py --apply` 的整文件序列化器断言要求 `json.dumps(doc, indent=1,
  ensure_ascii=False) + "\\n" == raw`; 而当前 registry **尾换行被移除**
  (`5576e72`(EXP1-Q27) 尾字节 `0a 7d 0a` → `058bc77`(R479) 尾字节 `22 0a 7d`)
  ⇒ 整文件改写路径结构上被禁用 (fail-closed, 保护了文件未被重排)。

纪律 (R409 / 共享台账):
  * 断言失败 ⇒ **改用文本插入** (在锚点行做字符串拼接), **绝不静默重排整份文件**;
  * 写入前断言「块级序列化器逐字节复现原块」—— 全文件复现不可得时, 把不变量降到**块级**
    并证明「改动字节被限制在该块内」;
  * 幂等 (重跑不重复插入) + 写后读回校验 (不只信工具回执);
  * 派生值取自 `bind_evidence.derive()` **同一函数** (口径单源, 禁手写字段值);
  * 保留文件原有尾字节约定 (不顺手加尾换行 —— 那是另一写者的约定, 另行仲裁)。

用法:
  python3 eval/capability/exp1-q28/apply_row_text_insert_q28.py --row-id probe.randomized-selfcheck [--write]
退出码: 0 成功或已是最新 / 2 断言失败 / 3 环境或测量失败。
"""
import argparse
import difflib
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CAP = ROOT / 'eval' / 'capability'
sys.path.insert(0, str(CAP))
import bind_evidence as be  # noqa: E402

FIELD = 'evidence_generated_with'
INDENT_PREFIX = '   '          # 行对象在 rows 数组内的缩进 (3 空格; 与文件现状一致)


def render_block(name, d):
    """块渲染: `json.dumps(indent=1)` 后整体右移 INDENT_PREFIX —— 与文件现状逐字节一致。"""
    body = json.dumps(d, indent=1, ensure_ascii=False)
    lines = body.split('\n')
    return '\n'.join([name + ': ' + lines[0]] + [INDENT_PREFIX + ln if ln else ln for ln in lines[1:]])


def find_block(raw, row_id):
    """定位该行 FIELD 的块文本 (字符串感知花括号匹配)。返回 (start, end_text)。"""
    anchor = '"id": "%s"' % row_id
    if raw.count(anchor) != 1:
        raise RuntimeError('锚点不唯一: %s x%d' % (anchor, raw.count(anchor)))
    i = raw.index(anchor)
    key = '"%s"' % FIELD
    j = raw.index(key, i)
    k = raw.index('{', j)
    depth, in_str, esc = 0, False, False
    for p in range(k, len(raw)):
        c = raw[p]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return j, raw[j:p + 1]
    raise RuntimeError('块未闭合')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--row-id', required=True)
    ap.add_argument('--round', default='EXP1-Q28')
    ap.add_argument('--set-evidence-path', default='',
                    help='外科式改写该行 evidence_path (文本级, 限行区内唯一字面量)')
    ap.add_argument('--write', action='store_true', help='缺省为 dry-run')
    a = ap.parse_args()

    be.AUDITED_BY_ROUND = a.round
    root = be.repo_root()
    reg_abs = os.path.join(root, be.REG)
    with open(reg_abs, encoding='utf-8', newline='') as fh:
        raw = fh.read()
    raw_orig = raw
    doc = json.loads(raw)
    row = [r for r in doc['rows'] if r.get('id') == a.row_id]
    if len(row) != 1:
        print('FATAL: 行定位失败 %s' % a.row_id)
        return 3
    row = row[0]

    tracked, dirty = be.git_state(root)
    if not be.needs_field(row):
        print('NOOP: 该行不需要派生字段')
        return 0
    derived = be.derive(root, row, tracked, dirty)
    declared = row.get(FIELD)

    j, block = find_block(raw, a.row_id)

    # ---- 外科式 evidence_path 改写 (文本级, 限行区内唯一字面量) ----------------
    ep_old = None
    if a.set_evidence_path:
        anchor = '"id": "%s"' % a.row_id
        i0 = raw.index(anchor)
        keyc = '"evidence_path":'
        if raw[i0:j].count(keyc) != 1:
            print('FATAL: evidence_path 在行区内不唯一 x%d' % raw[i0:j].count(keyc))
            return 3
        m = re.search(r'"evidence_path":\s*"((?:[^"\\]|\\.)*)"', raw[i0:j])
        if not m:
            print('FATAL: evidence_path 字面量未匹配')
            return 3
        ep_old = json.loads('"%s"' % m.group(1))
        if ep_old != row.get('evidence_path'):
            print('FATAL: evidence_path 解析值 %r != 行字段 %r' % (ep_old, row.get('evidence_path')))
            return 3
        sub = raw[i0:j]
        new_sub = sub.replace(m.group(0), '"evidence_path": "%s"' % a.set_evidence_path, 1)
        raw = raw[:i0] + new_sub + raw[j:]
        tgt = ROOT / a.set_evidence_path
        if not tgt.exists():
            print('FATAL: 新证据面不存在 (fail-closed): %s' % a.set_evidence_path)
            return 3
        row['evidence_path'] = a.set_evidence_path
        j, block = find_block(raw, a.row_id)
        derived = be.derive(root, row, *be.git_state(root))

    old_dict = json.loads(block[len('"%s": ' % FIELD):])
    # 块级序列化器断言: 必须能逐字节复现**原块** (全文件复现不可得时的降级不变量)
    if render_block('"%s"' % FIELD, old_dict) != block:
        print('SER_ASSERT=FAIL 块级序列化器未能逐字节复现原块 (禁改写)')
        return 3
    print('SER_ASSERT=OK (块级逐字节复现)')

    if declared == derived:
        print('NOOP: 已是派生值 (幂等)')
        print('DERIVED=%s' % json.dumps(derived, ensure_ascii=False))
        return 0

    new_block = render_block('"%s"' % FIELD, derived)
    if raw.count(block) != 1:
        print('FATAL: 原块不唯一 x%d' % raw.count(block))
        return 3
    raw = raw.replace(block, new_block)

    # 读回校验: 解析 + 字段比对 + 改动被限制在该块 + 尾字节约定不变
    doc2 = json.loads(raw)
    row2 = [r for r in doc2['rows'] if r.get('id') == a.row_id][0]
    checks = {
        'field_applied': row2.get(FIELD) == derived,
        'evidence_path_applied': (not a.set_evidence_path) or row2.get('evidence_path') == a.set_evidence_path,
        'other_rows_untouched': all(
            r2 == r1 for r2, r1 in zip(doc2['rows'], doc['rows']) if r2.get('id') != a.row_id),
        'rows_n_same': len(doc2['rows']) == len(doc['rows']),
        'tail_convention_kept': raw[-2:] == raw_orig[-2:],
        'old_block_gone': raw.count(block) == 0,
        'new_block_once': raw.count(new_block) == 1,
    }
    orig_lines = raw_orig.split('\n')
    new_lines = raw.split('\n')
    # 改动定位: 原块行区间 (原文件坐标系) + evidence_path 行
    b_off = raw_orig.index(block)
    b_lo = raw_orig[:b_off].count('\n')
    b_hi = b_lo + block.count('\n')
    sm = difflib.SequenceMatcher(None, orig_lines, new_lines)
    diff = []
    stray = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        diff += ['-' + l for l in orig_lines[i1:i2]] + ['+' + l for l in new_lines[j1:j2]]
        for li in range(i1, i2):
            if b_lo <= li <= b_hi or '"evidence_path"' in orig_lines[li]:
                continue
            stray.append({'line': li + 1, 'text': orig_lines[li][:120]})
    checks['diff_confined_to_block'] = not stray
    bad = [k for k, v in checks.items() if not v]
    out = {'row_id': a.row_id, 'round': a.round, 'declared_before': declared, 'derived': derived,
           'evidence_path_before': ep_old, 'evidence_path_after': a.set_evidence_path or None,
           'checks': checks, 'diff_lines': len(diff), 'stray_changed_lines': stray,
           'changed_lines': diff, 'bytes_before': len(raw_orig),
           'bytes_after': len(raw), 'write': bool(a.write)}
    if bad:
        out['fails'] = bad
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 2

    if a.write:
        with open(reg_abs, 'w', encoding='utf-8', newline='') as fh:
            fh.write(raw)
        with open(reg_abs, encoding='utf-8', newline='') as fh:
            back = fh.read()
        out['readback_bytes_equal'] = (back == raw)
        if back != raw:
            out['fails'] = ['readback_bytes_equal']
            print(json.dumps(out, ensure_ascii=False, indent=1))
            return 2
        # 幂等复核: 以写后的文件重新派生 ⇒ 必须等于已声明值
        doc3 = json.loads(back)
        r3 = [r for r in doc3['rows'] if r.get('id') == a.row_id][0]
        d3 = be.derive(root, r3, *be.git_state(root))
        out['idempotent_after_write'] = (d3 == r3.get(FIELD))
        if not out['idempotent_after_write']:
            out['fails'] = ['idempotent_after_write']
            print(json.dumps(out, ensure_ascii=False, indent=1))
            return 2

    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
