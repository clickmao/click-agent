#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q40 · 候选④: 提交面「尾 LF 契约」闸 (opt-in, 默认**关**)。

契约名与违规原因码**不在此处定义** —— 从 `bind_evidence.py` 取 (单一权威源):
`TAIL_CONTRACT=R481-tail-lf` / `NONCANON_REASON=tail_lf_missing`。本件只声明**作用面**
(哪些件受该契约约束) 与**提交面取值方式**, 不另立一份规范。

提交面语义 (R-Q39 的「记录 → 重审」教训): 判据必须取**将被提交的字节** ——
  ① 已 staged ⇒ `git show :<path>` (index 版本, 即 committed 后会变成的内容);
  ② 未 staged 但在 HEAD ⇒ `git show HEAD:<path>`;
  ③ 两者皆无 (新件) ⇒ 工作区字节;
  ④ 三者皆不可得 ⇒ **fail-closed 判红** (不可判 ≠ 合规)。

判据: 末字节为 LF ∧ 无 CRLF ∧ 无 BOM。三态退出码: 0 全绿 / 2 判据红 / 3 环境不可判。
默认作用面 = DEFAULT_TARGETS (可用 --targets <file> 覆盖: 每行一个仓内相对路径, 空行/# 忽略)。
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'eval' / 'capability'))
try:
    import bind_evidence as be                      # 契约名/原因码的单一权威源
    TAIL_CONTRACT, NONCANON_REASON = be.TAIL_CONTRACT, be.NONCANON_REASON
except Exception as exc:                            # 权威源不可得 ⇒ 不发明规范
    sys.stderr.write('TAIL_LF_GUARD: 契约权威源不可用 (%s) ⇒ rc=3\n' % exc)
    sys.exit(3)

# 默认作用面: 登记面里以「尾 LF 规范形」为一等字段的件 (exp1q31.only-equivalence 的输入族 +
#   登记表自身)。作用面是**声明**, 不是推断 —— 扩面须改这一行 (可审计)。
DEFAULT_TARGETS = ('docs/verification-registry.json', 'eval/capability/instruments.json')


def blob_bytes(rel):
    """按提交面语义取该件的字节; 返回 (bytes|None, source)。"""
    p = subprocess.run(['git', 'show', ':%s' % rel], cwd=str(ROOT), capture_output=True)
    if p.returncode == 0:
        return p.stdout, 'index'
    p = subprocess.run(['git', 'show', 'HEAD:%s' % rel], cwd=str(ROOT), capture_output=True)
    if p.returncode == 0:
        return p.stdout, 'head'
    f = ROOT / rel
    if f.is_file():
        return f.read_bytes(), 'worktree'
    return None, 'unresolved'


def judge(raw):
    """(是否合规, 原因)。判据 = 末字节 LF ∧ 无 CRLF ∧ 无 BOM。"""
    if not raw:
        return False, 'empty_or_unresolved'
    if raw.startswith(b'\xef\xbb\xbf'):
        return False, 'bom_present'
    if b'\r\n' in raw:
        return False, 'crlf_present'
    if not raw.endswith(b'\n'):
        return False, NONCANON_REASON
    return True, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--targets', default=None, help='作用面清单文件 (每行一个仓内相对路径)')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--json', default=None)
    a = ap.parse_args()

    if a.targets:
        if not os.path.isfile(a.targets):
            sys.stderr.write('TAIL_LF_GUARD: 清单不可读 %s ⇒ rc=3 (fail-closed 由调用方决定)\n'
                             % a.targets)
            return 3
        targets = [ln.strip() for ln in open(a.targets, encoding='utf-8')
                   if ln.strip() and not ln.strip().startswith('#')]
    else:
        targets = list(DEFAULT_TARGETS)

    rows, bad, unresolved = [], [], []
    for rel in targets:
        raw, src = blob_bytes(rel)
        ok, why = judge(raw) if raw is not None else (False, 'unresolved')
        rows.append({'path': rel, 'source': src, 'ok': bool(ok), 'why': why,
                     'bytes': None if raw is None else len(raw),
                     'tail': None if not raw else ('LF' if raw.endswith(b'\n') else 'NONE')})
        if raw is None:
            unresolved.append(rel)
        elif not ok:
            bad.append(rel)

    print('TAIL_LF_GUARD contract=%s targets=%d violations=%d unresolved=%d'
          % (TAIL_CONTRACT, len(targets), len(bad), len(unresolved)))
    for r in rows:
        if not r['ok']:
            print('  VIOLATION %s source=%s why=%s bytes=%s' % (r['path'], r['source'], r['why'],
                                                                r['bytes']))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({'contract': TAIL_CONTRACT, 'rows': rows},
                                                   ensure_ascii=False, indent=1) + '\n',
                                        encoding='utf-8')
    if unresolved:
        print('TAIL_LF_GUARD_UNRESOLVED=%d ⇒ rc=2 (不可判 = 拦; 不判绿)' % len(unresolved))
        return 2
    if bad:
        print('TAIL_LF_GUARD_VIOLATIONS=%d ⇒ 终态要求: 末字节 LF ∧ 无 CRLF ∧ 无 BOM' % len(bad))
        return 2
    print('TAIL_LF_GUARD=OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
