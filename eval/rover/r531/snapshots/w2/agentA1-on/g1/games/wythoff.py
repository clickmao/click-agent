"""Wythoff 博弈: 可从单堆取任意正数, 或两堆同时取相同正数, 最后一颗者胜。

冷态 (先手必败点) 由 Beatty 序列 (floor(n*phi), floor(n*phi^2)) 判定。
"""
import math

_PHI = (1.0 + math.sqrt(5.0)) / 2.0
_PHI2 = _PHI * _PHI


def _beatty(n: int) -> int:
    """floor(n * phi) 的精确整数计算: (n + isqrt(5*n*n)) // 2。"""
    return (n + math.isqrt(5 * n * n)) // 2


def _cold(a: int, b: int) -> bool:
    """判定 (a,b) 是否为冷态 (无序)。"""
    if a > b:
        a, b = b, a
    if a == 0:
        return b == 0
    # 冷态满足 b - a == a_in_sequence 且 a == floor(n*phi), b == floor(n*phi^2)
    fa = _beatty(a)  # 若 a 是 floor(n*phi), 则 n ≈ ...
    for n in range(1, 40):
        p = _beatty(n)
        q = p + n
        if (a, b) == (p, q):
            return True
        if p > a:
            break
    return False


def is_cold(a: int, b: int) -> bool:
    return _cold(a, b)


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _cold(a, b):
        return 'LOSE'

    # 字典序最小必胜着法: 枚举 (i,j) 满足只动一堆或两堆同取, 到达冷态
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _cold(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
