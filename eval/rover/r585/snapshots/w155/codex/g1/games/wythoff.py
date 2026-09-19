"""Wythoff's game: lexicographically smallest winning move, or LOSE."""

LIMIT = 25


def _win_table(limit: int):
    win = [[False] * (limit + 1) for _ in range(limit + 1)]
    for total in range(1, 2 * limit + 1):
        for a in range(limit + 1):
            b = total - a
            if b < 0 or b > limit:
                continue
            result = False
            for i in range(1, a + 1):
                if not win[a - i][b]:
                    result = True
                    break
            if not result:
                for j in range(1, b + 1):
                    if not win[a][b - j]:
                        result = True
                        break
            if not result:
                for i in range(1, min(a, b) + 1):
                    if not win[a - i][b - i]:
                        result = True
                        break
            win[a][b] = result
    return win


_WIN = _win_table(LIMIT)


def solve(text: str) -> str:
    a, b = (int(v) for v in text.split()[:2])
    if not _WIN[a][b]:
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if not _WIN[a - i][b - j]:
                return "WIN %d %d" % (i, j)
    return "LOSE"
