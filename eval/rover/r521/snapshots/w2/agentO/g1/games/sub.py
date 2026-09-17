#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""games/sub.py — 子游戏 (subtraction game) 必胜/必败判定

问题定义
--------
给定一堆石子 n, 每次可取走集合 moves 中的任意一个正整数个石子 (不超过当前堆)。
两名玩家轮流取, 取走最后一颗石子者取胜 (normal play, 取尽者胜)。

经典的"取石子游戏"特例:
  每次可取 1..m 颗 (moves = {1,...,m})  ⇒ 必败点 = n % (m+1) == 0
  只能取固定集合 (如 {1,3,4})            ⇒ 必败点由 SG/DP 递推给出

输入 (STDIN 整体)
-----------------
第一行: n  m          n = 石子数, m = 可取的最大颗数 (每次可取 1..m 颗)
后续行(可选): k  a1 a2 ... ak   若给出, 则每次可取集合为 {a1,...,ak} (正整数)
                        —— 给了这一行时, 第一行的 m 只用于校验/忽略, 以集合为准。

也接受单行形式 (空格/逗号分隔, 方便测试):  n,m  或  n;a1,a2,...

输出 (STDOUT)
-------------
一行: "WIN" 或 "LOSE"  (先手必胜 / 先手必败), 不打印任何多余文字。

API
---
solve(text) -> str  : 返回 "WIN" 或 "LOSE"; text 为完整输入字符串。

依赖: 仅标准库。自检: python3 games/sub.py --selftest  → 打印 PASS/FAIL, 退出码 0=通过。
"""

from __future__ import annotations

import re
import sys
from functools import reduce
from math import gcd


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------
def _ints(line: str):
    return [int(x) for x in re.findall(r"-?\d+", line)]


def _parse(text: str):
    """解析输入, 返回 (n, moves_tuple)。moves 为升序去重正整数元组。"""
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    if not lines:
        raise ValueError("empty input")

    nums = _ints(lines[0])
    if len(nums) < 1:
        raise ValueError("first line needs n")
    n = nums[0]
    if n < 0:
        raise ValueError("n must be >= 0")

    moves = None
    # 形式 B: 第二行以 k 开头, 后跟 k 个可取数
    if len(lines) >= 2:
        second = _ints(lines[1])
        if second:
            if len(second) >= 2 and second[0] == len(second) - 1:
                moves = second[1:]
            else:
                moves = second

    if moves is None:
        # 形式 A: 第一行 n m  ⇒ 可取 1..m
        m = nums[1] if len(nums) >= 2 else None
        if m is None or m < 1:
            raise ValueError("need moves set or m>=1")
        moves = list(range(1, m + 1))

    moves = tuple(sorted({x for x in moves if x > 0}))
    if not moves:
        raise ValueError("moves set empty (all non-positive)")
    return n, moves


# ---------------------------------------------------------------------------
# 判定
# ---------------------------------------------------------------------------
def solve(text: str) -> str:
    """先手是否必胜。返回 'WIN' 或 'LOSE'。"""
    n, moves = _parse(text)
    moves = tuple(x for x in moves if x <= n)  # 超过 n 的取法在此局面不可用
    if n == 0:
        return "LOSE"  # 无子可取, 当前局面先手已无法行动 ⇒ 负
    if not moves:
        return "LOSE"
    # 递推: win[i] = True 表示剩 i 颗时先手必胜
    #   win[i] = 存在 move<=i 使得 win[i-move] == False
    win = bytearray(n + 1)
    for i in range(1, n + 1):
        for mv in moves:
            if mv > i:
                break  # moves 已升序
            if not win[i - mv]:
                win[i] = 1
                break
    return "WIN" if win[n] else "LOSE"


# 常见特例: 每次可取 1..m 颗时的闭式判据 (用于交叉验证)
def _closed_form_1_to_m(n: int, m: int) -> str:
    return "LOSE" if (n % (m + 1)) == 0 else "WIN"


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------
def _selftest() -> int:
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append("%s: got=%r want=%r" % (name, got, want))

    # 1) 闭式对照: 取 1..m, 必败当且仅当 n % (m+1)==0
    for m in (1, 2, 3, 5):
        for n in range(0, 60):
            check("1..%d n=%d" % (m, n),
                  solve("%d %d\n" % (n, m)),
                  _closed_form_1_to_m(n, m))

    # 2) 单颗取法: 只能取 1 (moves={1}) ⇒ 奇数胜
    check("only1 n=1", solve("1\n1 1\n"), "WIN")
    check("only1 n=2", solve("2\n1 1\n"), "LOSE")
    check("only1 n=3", solve("3\n1 1\n"), "WIN")

    # 3) 已知固定集合 {1,3,4}: 必败点 = 0,2,7,9,14,16,... (period 7, since lcm-ish窗口)
    #    手工递推前若干项验证
    LOSE_134 = {0, 2, 7, 9, 14, 16, 21, 23}
    for n in range(0, 24):
        want = "LOSE" if n in LOSE_134 else "WIN"
        check("134 n=%d" % n, solve("%d\n3 1 3 4\n" % n), want)

    # 4) n=0 必败
    check("n=0 A", solve("0 3\n"), "LOSE")
    check("n=0 B", solve("0\n1 5\n"), "LOSE")

    # 5) 取法去重/排序: 重复取法不改变结果
    check("dup", solve("10\n4 2 2 3 1\n"), solve("10\n3 1 2 3\n"))

    # 6) 取法超过 n: 全部不可用 ⇒ 必败
    check("mv>n", solve("2\n1 5\n"), "LOSE")

    # 7) 负向控制: 若把 "取尽者胜" 错实现成 "取尽者负" (misère), blinker 式对照必须变红。
    #    这里直接断言 normal-play 的已知值, 反向注入实现时该组必红。
    check("normal-play n=4 m=2", solve("4 2\n"), "WIN")
    check("normal-play n=3 m=2", solve("3 2\n"), "LOSE")

    if fails:
        sys.stdout.write("FAIL\n")
        for f in fails:
            sys.stdout.write("  " + f + "\n")
        return 1
    sys.stdout.write("PASS\n")
    return 0


def main(argv):
    if "--selftest" in argv:
        return _selftest()
    data = sys.stdin.read()
    sys.stdout.write(solve(data) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
