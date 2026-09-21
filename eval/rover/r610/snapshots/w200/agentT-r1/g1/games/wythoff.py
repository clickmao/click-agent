"""wythoff: Wythoff 博弈必胜手（字典序最小）。

输入格式：
    一行两个整数 a b（两堆石子数）
输出：LOSE 或 WIN i j（从第一堆取 i、从第二堆取 j，字典序最小）。
"""


def cold_pairs(limit: int):
    """返回所有冷点 (p, q)（p <= q，p < limit），由 Beatty 序列生成。"""
    pairs = []
    seen = set()
    n = 0
    while True:
        p = int(n * 1.618033988749895)
        q = int(n * 2.618033988749895)
        if q - p != n:
            p += 1
        seen.add(p)
        seen.add(q)
        pairs.append((p, q))
        if p >= limit or q >= limit:
            break
        n += 1
    return pairs


def is_cold(a: int, b: int, pairs) -> bool:
    lo, hi = min(a, b), max(a, b)
    for p, q in pairs:
        if (p, q) == (lo, hi):
            return True
        if p > lo:
            return False
    return False


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    pairs = cold_pairs(max(a, b))
    if is_cold(a, b, pairs):
        return "LOSE"

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            legal = (i == 0) or (j == 0) or (i == j)
            if not legal:
                continue
            na, nb = a - i, b - j
            if na == 0 and nb == 0:
                return "WIN %d %d" % (i, j)
            if is_cold(na, nb, pairs):
                return "WIN %d %d" % (i, j)
    return "LOSE"
