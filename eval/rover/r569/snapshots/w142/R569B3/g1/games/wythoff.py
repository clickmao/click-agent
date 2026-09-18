"""Wythoff game: losing-position test and lexicographically minimal winning move."""


def solve(text: str) -> str:
    a, b = map(int, text.split())
    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            same = (i == j)
            one_pile = (i == 0 or j == 0)
            if not (same or one_pile):
                continue
            moves.append((i, j))
    moves.sort()
    for i, j in moves:
        lose = False
        x, y = a - i, b - j
        if x > y:
            x, y = y, x
        d = y - x
        t = (1 + 5 ** 0.5) / 2
        if x == int(d * t) and y == x + d:
            lose = True
        if lose:
            return "WIN %d %d" % (i, j)
    return "LOSE"
