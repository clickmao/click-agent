"""Wythoff's game: lexicographically smallest winning move (i, j)."""

LIMIT = 64


def _cold_table(limit=LIMIT):
    # Cold (P-)positions of Wythoff's game up to coordinate `limit`.
    table = set()
    used = set()
    n = 0
    while True:
        a = n
        while a in used:
            a += 1
        b = a + n
        if a > limit or b > limit:
            break
        table.add((a, b))
        table.add((b, a))
        used.add(a)
        used.add(b)
        n += 1
    return table


_COLD = _cold_table()


def _is_cold(a, b):
    if a == 0 and b == 0:
        return True
    return (a, b) in _COLD


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            na, nb = a - i, b - j
            if _is_cold(na, nb):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand

    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
