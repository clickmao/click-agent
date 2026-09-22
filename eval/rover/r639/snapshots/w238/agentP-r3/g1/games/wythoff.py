LIMIT = 25


def _build_table():
    lose = [[True] * (LIMIT + 1) for _ in range(LIMIT + 1)]
    for a in range(LIMIT + 1):
        for b in range(LIMIT + 1):
            if a == 0 and b == 0:
                continue
            win = False
            for i in range(a + 1):
                for j in range(b + 1):
                    if i == 0 and j == 0:
                        continue
                    if i != 0 and j != 0 and i != j:
                        continue
                    if i > a or j > b:
                        continue
                    if lose[a - i][b - j]:
                        win = True
                        break
                if win:
                    break
            lose[a][b] = not win
    return lose


_TABLE = None


def solve(text):
    global _TABLE
    if _TABLE is None:
        _TABLE = _build_table()
    a, b = (int(x) for x in text.split())
    if a > b:
        a, b = b, a
    if _TABLE[a][b]:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if i > a or j > b:
                continue
            if _TABLE[a - i][b - j]:
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
