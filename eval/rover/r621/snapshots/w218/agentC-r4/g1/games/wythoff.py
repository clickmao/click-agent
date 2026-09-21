"""Wythoff 博弈: 判定必败点或给出字典序最小的必胜着法。

stdin: 一行 "a b"。
stdout: "LOSE" 或 "WIN i j", 末尾不带换行。
"""
import math


def _is_losing(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    an = int(math.floor(d * (1 + math.sqrt(5)) / 2.0))
    return a == an


def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    if _is_losing(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na = a - i
            nb = b - j
            if _is_losing(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
