"""Wythoff's game: find the lexicographically smallest winning move.

Legal removal vector (i, j), with i, j >= 0 and i+j > 0:
  - i == 0, j > 0  : take j stones from pile 2 only
  - i > 0,  j == 0 : take i stones from pile 1 only
  - i == j > 0     : take the same positive amount from both piles

A move is winning when it reaches a losing (P) position.  Wythoff's
P-positions are (floor(n*phi), floor(n*phi)+n) and their mirrors.
Enumerating (i, j) in lexicographic order returns the required move.
"""

_POS = None


def _positions():
    global _POS
    if _POS is None:
        phi = (1 + 5 ** 0.5) / 2
        pos = set()
        for n in range(0, 64):
            x = int(n * phi)
            y = x + n
            pos.add((x, y))
            pos.add((y, x))
        _POS = pos
    return _POS


def _legal(i: int, j: int) -> bool:
    if i == 0 or j == 0:
        return True
    return i == j


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    pos = _positions()

    if (a, b) in pos:
        return "LOSE"

    for i in range(a + 1):
        for j in range(b + 1):
            if (i, j) == (0, 0) or not _legal(i, j):
                continue
            if (a - i, b - j) in pos:
                return "WIN %d %d" % (i, j)
    return "LOSE"
