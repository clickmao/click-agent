"""Wythoff's game: LOSE for cold (P-)positions, else lexicographically minimal winning move."""

W = 30


def _cold_table():
    win = [[False] * (W + 1) for _ in range(W + 1)]
    for a in range(W + 1):
        for b in range(W + 1):
            if a == 0 and b == 0:
                win[a][b] = False
                continue
            w = False
            for i in range(1, a + 1):
                if not win[a - i][b]:
                    w = True
                    break
            if not w:
                for j in range(1, b + 1):
                    if not win[a][b - j]:
                        w = True
                        break
            if not w:
                for t in range(1, min(a, b) + 1):
                    if not win[a - t][b - t]:
                        w = True
                        break
            win[a][b] = w
    return win


WIN = _cold_table()


def solve(text):
    a, b = map(int, text.split())
    if not WIN[a][b]:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0) or i == j:
                if not WIN[a - i][b - j]:
                    return 'WIN %d %d' % (i, j)
    return 'LOSE'
