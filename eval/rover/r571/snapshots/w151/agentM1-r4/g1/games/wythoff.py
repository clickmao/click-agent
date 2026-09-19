"""Wythoff 博弈：先手必败判定；必胜时按字典序最小的 (i, j)（两堆各取走的石子数）。"""


def _losing_set(limit: int):
    lose = set()
    pi = 0
    for k in range(0, 64):
        x = k * (1 + 5 ** 0.5) / 2.0
        n = int(x) + pi
        pi = 0
        while n * n > k * k + k + 1:
            n -= 1
            pi = 1
        while not ((n + 1) * n <= k * k + k + 1):
            n -= 1
        while not (n * n <= k * k + k + 1 < (n + 1) * n):
            n += 1
        m = n + k
        if n > limit:
            break
        lose.add((n, m))
        lose.add((m, n))
    return lose


def _loss(n: int) -> int:
    r = int(n * (1 + 5 ** 0.5) / 2.0)
    while r * r > n * n + n:
        r -= 1
    while (r + 1) * (r + 1) <= n * n + n:
        r += 1
    return r


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())
    r = _loss(min(a, b))
    if a == r and b == r + min(a, b):
        return 'LOSE'
    if b == r and a == r + min(a, b):
        return 'LOSE'
    best = None
    # 单堆取法
    for t in range(0, a + 1):
        for u in range(0, b + 1):
            if t == 0 and u == 0:
                continue
            same = (t == u)
            one = (t == 0 or u == 0)
            if not (same or one):
                continue
            na, nb = a - t, b - u
            if (na, nb) in _losing_pair(na, nb):
                cand = (t, u)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])


def _losing_pair(na, nb):
    if na < 0 or nb < 0:
        return set()
    r = _loss(min(na, nb))
    d = abs(na - nb)
    return {(r, r + d), (r + d, r)}
