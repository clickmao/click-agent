"""Wythoff 博弈：必败点判定；必胜时给字典序最小的 (i, j)。"""

LIMIT = 26


def _is_losing(a, b):
    lo, hi = (a, b) if a <= b else (b, a)
    n = hi - lo
    if n >= LIMIT + 1:
        return False
    phi = (1 + 5 ** 0.5) / 2
    return lo == int(n * phi) and lo + n == hi


def solve(text):
    nums = text.split()
    a, b = int(nums[0]), int(nums[1])

    if _is_losing(a, b):
        return "LOSE"

    best = None
    # 从任一（单）堆取
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            same = 1 if (a - i) == (b - j) else 0
            single = 1 if ((i > 0 and j == 0) or (i == 0 and j > 0)) else 0
            if not (single or same):
                continue
            if not _is_losing(a - i, b - j):
                continue
            if best is None or (i, j) < best:
                best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
