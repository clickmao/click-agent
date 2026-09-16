#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 候选⑦: 跨写者提交纪律 —— `staged == 本轮声称的 artifact 清单`。

动机 (AB.6② 实测事故): 同 gateway 下的兄弟作业/前台循环与自检作业**共享同一工作树**。
一次 `git add -A` / 整树 add 会把**别的执行体的半成品**（未完成改动、他人证据）一并提交,
而提交本身不报错 ⇒ 归属混乱在事后才被发现 (R481 曾为此回退 96 行纯归属漂移)。
本器把「提交内容 = 本轮声明清单」变成**提交前的机检闸**:
  · staged ⊃ 清单 (多出来的 = 对侧在飞文件) ⇒ 拒绝提交 (rc=2), 并逐条列出多出的路径;
  · staged ⊂ 清单 (声明了却没 staged) ⇒ 拒绝提交 (rc=2);
  · 两侧相等 ⇒ 放行 (rc=0)。

用法:
  python3 eval/capability/exp1-q30/stage_guard_q30.py --list <清单文件>        # 真机核验当前索引
  python3 eval/capability/exp1-q30/stage_guard_q30.py --selftest              # 纯函数夹具 (无 git 依赖)
清单格式: 每行一个仓库相对路径; `#` 起注释; 空行忽略。
"""
import subprocess
import sys


def norm(lines):
    out = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith('#'):
            continue
        out.append(s.strip('"'))
    return out


def verdict(declared, staged):
    """纯函数: 返回 (ok, extra_staged, missing). 两侧都按集合语义比较 (顺序无关, 重复去重)。"""
    d, s = set(declared), set(staged)
    extra, missing = sorted(s - d), sorted(d - s)
    return (not extra and not missing), extra, missing


def staged_paths():
    p = subprocess.run(['git', 'diff', '--cached', '--name-only'], capture_output=True, text=True, check=True)
    return norm(p.stdout.splitlines())


FIXTURES = [
    ('exact_match', ['a/b.py', 'c/d.json'], ['a/b.py', 'c/d.json'], True),
    ('foreign_extra_staged', ['a/b.py'], ['a/b.py', 'sibling/half-done.py'], False),
    ('declared_but_not_staged', ['a/b.py', 'c/d.json'], ['a/b.py'], False),
    ('both_empty', [], [], True),
    ('order_and_dup_insensitive', ['a/b.py', 'a/b.py', 'c/d.json'], ['c/d.json', 'a/b.py'], True),
    ('comments_and_blanks', ['# 本轮', '', 'a/b.py'], ['a/b.py'], True),
    ('same_count_wrong_content', ['a/b.py'], ['sibling/x.py'], False),
]


def selftest():
    bad = 0
    for name, decl, stg, want_ok in FIXTURES:
        ok, extra, missing = verdict(norm(decl), norm(stg))
        flag = 'OK' if ok == want_ok else 'FAIL'
        if ok != want_ok:
            bad += 1
        print('%-26s expect_ok=%-5s got=%-5s extra=%s missing=%s  %s'
              % (name, want_ok, ok, extra, missing, flag))
    # 负控: 若把判据退化成「只比条数」, `same_count_wrong_content` 夹具必须漏检 ⇒ 证明本判据非空心
    nc_decl, nc_stg, nc_want = FIXTURES[-1][1], FIXTURES[-1][2], FIXTURES[-1][3]
    n_only_ok = (len(norm(nc_decl)) == len(norm(nc_stg)))
    print('NC_len_only_comparison_would_miss=%s (期望 True: 条数相同、内容不同 ⇒ 条数口径漏检)' % n_only_ok)
    if not (n_only_ok and nc_want is False):
        print('NC_SETUP_FAIL: 夹具未能构造出「条数相同但内容不同」的形态')
        bad += 1
    print('SELFTEST %s (%d/%d)' % ('PASS' if bad == 0 else 'FAIL', len(FIXTURES) - bad, len(FIXTURES)))
    return 0 if bad == 0 else 2


def main():
    if '--selftest' in sys.argv:
        return selftest()
    if '--list' not in sys.argv:
        print('用法: --list <清单文件> | --selftest')
        return 3
    path = sys.argv[sys.argv.index('--list') + 1]
    declared = norm(open(path, encoding='utf-8').read().splitlines())
    staged = staged_paths()
    ok, extra, missing = verdict(declared, staged)
    print('STAGE_GUARD declared=%d staged=%d' % (len(declared), len(staged)))
    for p in extra:
        print('  EXTRA_STAGED (对侧在飞/未声明 ⇒ 禁提交): %s' % p)
    for p in missing:
        print('  MISSING (已声明未 staged): %s' % p)
    print('STAGE_GUARD=%s' % ('OK' if ok else 'REFUSE'))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
