"""Wythoff 博弈: 必败点判定与字典序最小的必胜着法。"""

MAXN = 30


def _win_table():
    win = [[False] * (MAXN + 1) for _ in range(MAXN + 1)]
    for a in range(MAXN + 1):
        for b in range(MAXN + 1):
            if a == 0 and b == 0:
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


WIN = _win_table()


def solve(text):
    a, b = map(int, text.split()[:2])
    if not WIN[a][b]:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if not WIN[na][nb]:
                best = (i, j)
                break
        if best is not None:
            break
    i, j = best
    return 'WIN %d %d' % (i, j)
