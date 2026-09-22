"""Wythoff's game: lexicographically smallest winning move."""
MAX = 25


def _is_lose(a, b, lose):
    if a > b:
        a, b = b, a
    return lose[a][b]


def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])

    lose = [[False] * (MAX + 1) for _ in range(MAX + 1)]
    lose[0][0] = True
    for s in range(1, 2 * MAX + 1):
        for x in range(0, MAX + 1):
            y = s - x
            if y < 0 or y > MAX or x > y:
                continue
            if x == 0 and y == 0:
                continue
            win = False
            # remove from pile y only (or x only)
            for t in range(0, x):
                if lose[t][y]:
                    win = True
                    break
            if not win:
                for t in range(0, y):
                    if x < t:
                        pass
                    aa, bb = (x, t) if x <= t else (t, x)
                    if lose[aa][bb]:
                        win = True
                        break
            if not win:
                for d in range(1, min(x, y) + 1):
                    if lose[x - d][y - d]:
                        win = True
                        break
            lose[x][y] = not win

    def orig_lose(u, v):
        if u > v:
            u, v = v, u
        return lose[u][v]

    if orig_lose(a, b):
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if orig_lose(na, nb):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
