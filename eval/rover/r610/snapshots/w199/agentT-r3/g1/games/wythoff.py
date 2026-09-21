"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。"""


def _lose(a: int, b: int) -> bool:
    x, y = min(a, b), max(a, b)
    # 必败点满足 y - x = t 且 x = floor(t * phi)，其中 phi = (1+sqrt(5))/2。
    # 用整数比较精确判定 floor(t*phi) >= mid <=> t*phi >= mid <=> t^2*phi^2 >= mid^2
    # 5*phi^2 = (3+sqrt(5))^2/... 直接使用 5t^2 >= (2mid - t)^2 的等价形式。
    t = y - x
    if t == 0:
        return x == 0
    lo, hi = 0, 64
    while lo < hi:
        mid = (lo + hi + 1) // 2
        # floor(t*phi) >= mid  <=>  t*phi >= mid  <=>  (2t - t)*? 用 5t^2 与 (2mid - t)^2 比较:
        # t*phi = t*(1+sqrt5)/2;  2t*phi = t + t*sqrt5;  t*phi >= mid <=> t*sqrt5 >= 2*mid - t
        # 两边不含负号时再平方: 5t^2 >= (2mid - t)^2
        if 2 * mid - t <= 0 or 5 * t * t >= (2 * mid - t) * (2 * mid - t):
            lo = mid
        else:
            hi = mid - 1
    return x == lo


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    if _lose(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if (i == 0 or j == 0 or i == j) and _lose(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN " + str(best[0]) + " " + str(best[1])
