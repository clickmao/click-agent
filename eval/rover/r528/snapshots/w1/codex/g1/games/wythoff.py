"""Wythoff's game: lexicographically smallest winning move (i, j)."""


def solve(text: str) -> str:
    a, b = map(int, text.split())
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            moves.append((i, j, na, nb))
    moves.sort(key=lambda mv: (mv[0], mv[1]))
    win = {}
    for i in range(a + 1):
        for j in range(b + 1):
            win[(i, j)] = False
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            result = False
            for di in range(i + 1):
                for dj in range(j + 1):
                    if di == 0 and dj == 0:
                        continue
                    if di > 0 and dj > 0 and di != dj:
                        continue
                    if not win[(i - di, j - dj)]:
                        result = True
                        break
                if result:
                    break
            win[(i, j)] = result
    if not win[(a, b)]:
        return "LOSE"
    for i, j, na, nb in moves:
        if not win[(na, nb)]:
            return "WIN %d %d" % (i, j)
    return "LOSE"
