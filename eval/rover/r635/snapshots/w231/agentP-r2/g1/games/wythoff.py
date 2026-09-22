"""Wythoff's game: lexicographically smallest winning move (i, j), or LOSE.

Input text: one line 'a b'.
Output text: 'WIN i j' or 'LOSE'.
"""


def _lose(a: int, b: int) -> bool:
    if a == b:
        return a == 0
    lo, hi = (a, b) if a < b else (b, a)
    t = hi - lo
    return lo == int(t * (1 + 5 ** 0.5) / 2)


def solve(text: str) -> str:
    lines = text.split('\n')
    head = lines[0].split() if lines else []
    if len(head) < 2:
        return 'LOSE'
    a, b = (int(x) for x in head[:2])
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            moves.append((i, j))
    for i, j in sorted(moves):
        if _lose(a - i, b - j):
            return 'WIN %d %d' % (i, j)
    return 'LOSE'
