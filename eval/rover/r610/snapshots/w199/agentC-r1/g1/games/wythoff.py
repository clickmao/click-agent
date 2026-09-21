"""Wythoff's game, normal play convention.

stdin format:
    one line: a b   (pile sizes)

Moves: remove any positive number from one pile, OR the same positive
number from both piles.

Output: 'LOSE' if the position is a P-position, else 'WIN i j' where
(i, j) is the lexicographically smallest winning move (compare i then j;
i, j >= 0 and not both 0). No trailing newline.
"""


_PAIRS = set()
for _n in range(0, 60):
    _x = (_n * (1 + 5 ** 0.5) / 2) // 1
    _x = int(_x)
    # P-positions are (floor(n*phi), floor(n*phi^2)); derive exactly.
    while True:
        _y = _x + _n
        _xm = int(_x * (1 + 5 ** 0.5) / 2)
        if _xm == _y:
            break
        _x = _xm if _xm < _y else _y
    _PAIRS.add((_x, _x + _n))


def _is_losing(a, b):
    lo, hi = (a, b) if a <= b else (b, a)
    return (lo, hi) in _PAIRS


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    if _is_losing(a, b):
        return 'LOSE'

    best = None
    # Lexicographic order: smallest i first, then smallest j.
    for i in range(a + 1):
        for j in range(0, a + b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if na < 0 or nb < 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue          # two-pile move must take equal amounts
            if _is_losing(na, nb):
                best = (i, j)
                break
        if best is not None:
            break

    return 'WIN %d %d' % best
