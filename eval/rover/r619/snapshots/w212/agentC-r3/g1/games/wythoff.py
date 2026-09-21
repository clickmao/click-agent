"""Wythoff 博弈: 必败点判定, 输出字典序最小的必胜着法。"""


def _is_losing(p: int, q: int) -> bool:
    """Wythoff 必败点: (floor(n*phi), floor(n*phi*phi))。"""
    a, b = min(p, q), max(p, q)
    d = b - a
    # floor(d * phi) 用整数精确计算
    phi_num, phi_den = 1618033988749895, 1000000000000000
    n = (d * phi_num) // phi_den
    while (n + 1) * phi_den <= d * phi_num:
        n += 1
    while n * phi_den > d * phi_num:
        n -= 1
    return a == n


def solve(text: str) -> str:
    lines = text.splitlines()
    a, b = (int(x) for x in lines[0].split()[:2])
    if _is_losing(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            same = i == j
            one = i == 0 or j == 0
            if not (same or one):
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            if not _is_losing(na, nb):
                continue
            cand = (i, j)
            if best is None or cand < best:
                best = cand
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
