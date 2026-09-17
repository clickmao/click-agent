"""Wythoff's game: lexicographically smallest winning move."""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    def losing(x, y):
        if x > y:
            x, y = y, x
        return x == int((y - x) * (1 + 5 ** 0.5) / 2)

    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j == 0) or (i == 0 and j > 0) or i == j:
                if losing(a - i, b - j):
                    moves.append((i, j))
    moves.sort()
    if not moves:
        return 'LOSE'
    i, j = moves[0]
    return 'WIN %d %d' % (i, j)
