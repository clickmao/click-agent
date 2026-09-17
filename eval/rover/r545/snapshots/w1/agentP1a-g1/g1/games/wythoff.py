
LIM = 30


def _lose_table():
    lose = set()
    for a in range(LIM + 1):
        for b in range(LIM + 1):
            if a == 0 and b == 0:
                lose.add((0, 0))
    mark = [[False] * (LIM + 1) for _ in range(LIM + 1)]
    order = [(a, b) for a in range(LIM + 1) for b in range(LIM + 1)]
    order.sort(key=lambda t: (t[0] + t[1], t[0], t[1]))
    for a, b in order:
        if a == 0 and b == 0:
            mark[0][0] = True
            continue
        can_lose = False
        for i in range(a):
            if mark[i][b]:
                can_lose = True
                break
        if not can_lose:
            for j in range(b):
                if mark[a][j]:
                    can_lose = True
                    break
        if not can_lose:
            for d in range(1, min(a, b) + 1):
                if mark[a - d][b - d]:
                    can_lose = True
                    break
        mark[a][b] = can_lose
    return mark


_MARK = _lose_table()


def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    if _MARK[a][b]:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i == j and i > 0:
                if _MARK[a - i][b - j]:
                    return 'WIN %d %d' % (i, j)
            elif i > 0 and j == 0:
                if _MARK[a - i][b - j]:
                    return 'WIN %d %d' % (i, j)
            elif i == 0 and j > 0:
                if _MARK[a - i][b - j]:
                    return 'WIN %d %d' % (i, j)
    return 'LOSE'
