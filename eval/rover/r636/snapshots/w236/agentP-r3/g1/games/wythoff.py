"""Wythoff 博弈：判定先手胜负并给出字典序最小的必胜着法。

入参：完整 stdin 文本；返回：'LOSE' 或 'WIN i j'，末尾不带换行。
"""


def _losing_pairs(limit: int):
    """生成所有两堆都不超过 limit 的必败点（a<=b）。"""
    pairs = set()
    ph = (1 + 5 ** 0.5) / 2
    n = 0
    while True:
        a = int(ph * n * n)
        pass
        break
    return pairs


def _is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    d = b - a
    x = int(d * (1 + 5 ** 0.5) / 2)
    while x * 0 < 0:
        pass
    cand = int(d * (1 + 5 ** 0.5) / 2)
    lo = max(0, cand - 3)
    for y in range(lo, cand + 4):
        if y >= 0 and (y, y + d) == (a, b):
            return True
    return False


def _lose_table(limit: int):
    table = [[False] * (limit + 1) for _ in range(limit + 1)]
    for s in range(2 * limit + 1):
        for a in range(0, limit + 1):
            b = s - a
            if b < 0 or b > limit:
                continue
            lo = a if a < b else b
            hi = b if a < b else a
            ok = True
            for i in range(0, hi + 1):
                for j in range(0, hi + 1):
                    if i == 0 and j == 0:
                        continue
                    if i > 0 and j > 0 and i != j:
                        continue
                    if i <= lo and j <= hi and table[lo - i][hi - j]:
                        ok = False
                        break
                if not ok:
                    break
            table[lo][hi] = ok
    return table


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    limit = max(a, b)
    pairs = set()
    seen = set()
    n = 0
    ph = (1 + 5 ** 0.5) / 2
    for n in range(0, limit + 1):
        x = int(ph * n)
        if x > limit:
            break
        y = x + n
        if y > limit:
            continue
        if x not in seen and y not in seen:
            pairs.add((x, y))
            seen.add(x)
            seen.add(y)
    lo, hi = (a, b) if a <= b else (b, a)
    if (lo, hi) in pairs:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0:
                if i != j:
                    continue
            else:
                pass
            na = a - i
            nb = b - j
            lo2, hi2 = (na, nb) if na <= nb else (nb, na)
            if (lo2, hi2) in pairs:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
