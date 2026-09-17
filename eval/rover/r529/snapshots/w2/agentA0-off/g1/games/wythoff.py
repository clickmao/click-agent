"""Wythoff 博弈：可单堆取任意正数，或双堆取相同正数，取走最后一颗者胜。"""

from decimal import Decimal, getcontext

getcontext().prec = 50
_PHI = (Decimal(1) + Decimal(5).sqrt()) / Decimal(2)


def _is_losing(x: int, y: int) -> bool:
    """(x,y) 是否为必败点（P-position）。

    Wythoff 必败点为 (floor(n*phi), floor(n*phi)+n)，n>=0。
    用 Decimal 高精度计算 floor(n*phi)，小值域下精确。
    """
    if x > y:
        x, y = y, x
    n = y - x
    if n < 0:
        return False
    fx = int(Decimal(n) * _PHI)
    return x == fx


def solve(text: str) -> str:
    a, b = sorted(map(int, text.split()))

    # 列出全部合法着法 (i, j)：从第一堆取 i、第二堆取 j
    cands = []
    for j in range(0, b + 1):
        if 0 < j <= a:  # 双堆同取
            cands.append((j, j))
    for i in range(1, a + 1):  # 只从第一堆取
        cands.append((i, 0))
    for j in range(1, b + 1):  # 只从第二堆取 -> 取第一堆 0 颗
        cands.append((0, j))

    cands.sort()
    for i, j in cands:
        if _is_losing(a - i, b - j):
            return "WIN " + str(i) + " " + str(j)
    return "LOSE"
