"""Wythoff's game: report the lexicographically smallest winning move."""

LIMIT = 30


def _win_table(limit):
    """win[a][b] is True iff (a, b) is an N-position."""
    win = [[False] * (limit + 1) for _ in range(limit + 1)]
    for a in range(limit + 1):
        for b in range(limit + 1):
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


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])
    win = _win_table(LIMIT)

    if not win[a][b]:
        return 'LOSE'

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if not win[a - i][b - j]:
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
