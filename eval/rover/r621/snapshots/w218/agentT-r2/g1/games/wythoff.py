"""Wythoff's game: losing positions on a 25x25 board."""

MAX = 30


def _build():
    lose = [[False] * MAX for _ in range(MAX)]
    for i in range(MAX):
        for j in range(MAX):
            good = False
            for a in range(1, i + 1):
                if lose[i - a][j]:
                    good = True
                    break
            if not good:
                for a in range(1, j + 1):
                    if lose[i][j - a]:
                        good = True
                        break
            if not good:
                for a in range(1, min(i, j) + 1):
                    if lose[i - a][j - a]:
                        good = True
                        break
            lose[i][j] = not good
    return lose


LOSE_TABLE = _build()


def solve(text):
    parts = text.split()
    a = int(parts[0])
    b = int(parts[1])
    if LOSE_TABLE[a][b]:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                if LOSE_TABLE[a - i][b - j]:
                    if best is None or (i, j) < best:
                        best = (i, j)
                    break
    return 'WIN %d %d' % best
