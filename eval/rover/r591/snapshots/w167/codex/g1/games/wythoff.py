"""Wythoff's game: report the lexicographically smallest winning move."""


def _losing_table(a, b):
    lost = [[False] * (b + 1) for _ in range(a + 1)]
    for x in range(a + 1):
        for y in range(b + 1):
            if x == 0 and y == 0:
                continue
            winning = False
            for i in range(1, x + 1):
                if not lost[x - i][y]:
                    winning = True
                    break
            if not winning:
                for j in range(1, y + 1):
                    if not lost[x][y - j]:
                        winning = True
                        break
            if not winning:
                for t in range(1, min(x, y) + 1):
                    if not lost[x - t][y - t]:
                        winning = True
                        break
            lost[x][y] = not winning
    return lost


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    lost = _losing_table(a, b)

    if lost[a][b]:
        return "LOSE"

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i <= a and j <= b and lost[a - i][b - j]:
                return "WIN %d %d" % (i, j)
    return "LOSE"
