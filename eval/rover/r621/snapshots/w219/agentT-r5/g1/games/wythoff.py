"""Wythoff 博弈：判定必败点，否则给出字典序最小的必胜着法。

入参 text: 一行 "a b"。
返回: "LOSE" 或 "WIN i j"，末尾不带换行。
约定: 每次可从任意一堆取任意正数目，或从两堆同时取相同正数目；取走最后一颗者胜。

判定: 轮到行动方必败当且仅当 (a, b) 为 Wythoff 对:
  a <= b 且 a == floor(phi * (b - a))，其中 phi = (1 + sqrt(5)) / 2。
必胜着法: 在全部合法着法中按 (i, j) 字典序最小者（先比 i 再比 j），
  其中 i 为从第一堆取走数、j 为从第二堆取走数，i, j >= 0 且不同时为 0。
"""

from math import isqrt


def _is_lose(x: int, y: int) -> bool:
    a, b = (x, y) if x <= y else (y, x)
    d = b - a
    # floor(phi * d)，用整数算术避免浮点误差：floor((d + isqrt(5*d*d)) / 2)
    t = (d + isqrt(5 * d * d)) // 2
    return a == t


def _moves(a: int, b: int):
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            yield i, j


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_lose(a, b):
        return "LOSE"
    for i, j in _moves(a, b):
        if _is_lose(a - i, b - j):
            return "WIN " + str(i) + " " + str(j)
    return "LOSE"
