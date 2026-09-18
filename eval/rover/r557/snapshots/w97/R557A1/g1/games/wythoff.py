"""Wythoff game: losing-position test with lexicographically smallest winning move."""

MAXN = 25 + 5


def _losing_table():
    lose = [[False] * (MAXN + 1) for _ in range(MAXN + 1)]
    for a in range(MAXN + 1):
        for b in range(MAXN + 1):
            if a == 0 and b == 0:
                lose[a][b] = True
                continue
            ok = False
            if a > 0 and lose[a - 1][b]:
                ok = True
            if not ok and b > 0 and lose[a][b - 1]:
                ok = True
            if not ok:
                d = min(a, b)
                if d > 0 and lose[a - d][b - d]:
                    ok = True
            lose[a][b] = not ok
    return lose


_LOSE = _losing_table()


def solve(text):
    a, b = (int(x) for x in text.split()[:2])
    if _LOSE[a][b]:
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if _LOSE[a - i][b - j]:
                return 'WIN %d %d' % (i, j)
    return 'WIN 0 0'
