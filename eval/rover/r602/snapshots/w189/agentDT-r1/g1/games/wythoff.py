_MAX = 25
_POS = {}


def _build():
    n = _MAX
    lose = [[False] * (n + 1) for _ in range(n + 1)]
    for i in range(n, -1, -1):
        for j in range(n, -1, -1):
            if i == 0 and j == 0:
                lose[i][j] = True
                continue
            w = False
            for t in range(1, i + 1):
                if lose[i - t][j]:
                    w = True
                    break
            if not w:
                for t in range(1, j + 1):
                    if lose[i][j - t]:
                        w = True
                        break
            if not w:
                for t in range(1, min(i, j) + 1):
                    if lose[i - t][j - t]:
                        w = True
                        break
            lose[i][j] = not w
    return lose


_LOSE = _build()


def solve(text):
    a, b = map(int, text.split()[:2])
    if _LOSE[a][b]:
        return 'LOSE'
    for i in range(0, a + 1):
        if i == 0:
            for j in range(1, b + 1):
                if _LOSE[a][b - j]:
                    return 'WIN %d %d' % (i, j)
        else:
            for j in range(0, b + 1):
                if _LOSE[a - i][b - j]:
                    return 'WIN %d %d' % (i, j)
    return 'LOSE'
