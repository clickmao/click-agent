"""Wythoff's game: take from one pile, or the same amount from both piles."""

MAX = 25

# losing[a][b] is True iff (a, b) is a losing position for the player about to move,
# where a legal move is (i, 0), (0, j) or (d, d) with d > 0.
_LOSING = [[False] * (MAX + 1) for _ in range(MAX + 1)]
for _a in range(MAX + 1):
    for _b in range(MAX + 1):
        if _a == 0 and _b == 0:
            continue
        _win = False
        for _d in range(1, _a + 1):
            if _LOSING[_a - _d][_b]:
                _win = True
                break
        if not _win:
            for _d in range(1, _b + 1):
                if _LOSING[_a][_b - _d]:
                    _win = True
                    break
        if not _win:
            for _d in range(1, min(_a, _b) + 1):
                if _LOSING[_a - _d][_b - _d]:
                    _win = True
                    break
        _LOSING[_a][_b] = not _win


def _is_losing(a: int, b: int) -> bool:
    return _LOSING[a][b]


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i and j and i != j:
                continue
            if _is_losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
