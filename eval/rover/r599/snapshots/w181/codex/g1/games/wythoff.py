"""Wythoff's game: lexicographically smallest winning move or LOSE."""

_MAX = 25


def _build() -> list:
    # win[a][b] is True when the player to move on (a, b) can force a win.
    win = [[False] * (_MAX + 1) for _ in range(_MAX + 1)]
    for a in range(_MAX + 1):
        for b in range(_MAX + 1):
            res = False
            for i in range(1, a + 1):
                if not win[a - i][b]:
                    res = True
                    break
            if not res:
                for j in range(1, b + 1):
                    if not win[a][b - j]:
                        res = True
                        break
            if not res:
                for d in range(1, min(a, b) + 1):
                    if not win[a - d][b - d]:
                        res = True
                        break
            win[a][b] = res
    return win


_WIN = _build()


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if not _WIN[a][b]:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not _WIN[a - i][b - j]:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
