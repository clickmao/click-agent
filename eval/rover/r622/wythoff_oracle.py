#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R622 · Wythoff 独立 oracle（**与判定器/生成器零共享代码**）。

来源 = R621 冻结题集里 `### 游戏 wythoff` 的**逐字规格**（题面文本，非期望输出）：
  读入一行 a b (1<=a<=25, 1<=b<=25)。
  先手必败 ⇒ 输出 `LOSE`；否则输出 `WIN i j`，其中 (i,j) = 全部必胜着法中按**字典序最小**
  （先比 i 再比 j；i,j>=0 且不同时为 0）。
  合法着法 = (i) 从任一堆取任意正数 或 (ii) 两堆同取 k>0。

实现路线（与生成器可能用的「冷点公式/Beatty 序列」**不同**）：按 a+b 升序的**直接定义 DP**
（losing(a,b) ⇔ 所有合法着法都到 winning 位），再枚举着法取字典序最小。
两者互为对照：公式法错则 DP 与期望输出不一致。
"""
from __future__ import annotations

MAXN = 25


def _build_losing(maxn: int = MAXN):
    """losing[a][b] = True ⇔ 轮到走的人必败（P 位）。按 a+b 升序填表（着法严格降 a+b）。"""
    los = [[False] * (maxn + 1) for _ in range(maxn + 1)]
    for t in range(0, 2 * maxn + 1):
        for a in range(0, maxn + 1):
            b = t - a
            if b < 0 or b > maxn:
                continue
            if a == 0 and b == 0:
                los[a][b] = True          # 无着法可取 ⇒ 到走者败
                continue
            any_to_losing = False
            for i in range(1, a + 1):      # 只取第一堆
                if los[a - i][b]:
                    any_to_losing = True
                    break
            if not any_to_losing:
                for j in range(1, b + 1):  # 只取第二堆
                    if los[a][b - j]:
                        any_to_losing = True
                        break
            if not any_to_losing:
                for k in range(1, min(a, b) + 1):   # 两堆同取
                    if los[a - k][b - k]:
                        any_to_losing = True
                        break
            los[a][b] = not any_to_losing
    return los


LOSING = _build_losing()


def legal_moves(a: int, b: int):
    for i in range(1, a + 1):
        yield (i, 0)
    for j in range(1, b + 1):
        yield (0, j)
    for k in range(1, min(a, b) + 1):
        yield (k, k)


def winning_moves(a: int, b: int):
    """全部必胜着法（取完到 P 位）。"""
    out = []
    for i, j in legal_moves(a, b):
        if LOSING[a - i][b - j]:
            out.append((i, j))
    return out


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    wm = winning_moves(a, b)
    if not wm:
        return "LOSE"
    i, j = min(wm)          # 字典序最小
    return "WIN %d %d" % (i, j)


if __name__ == "__main__":
    import sys
    print(solve(sys.stdin.read()))
