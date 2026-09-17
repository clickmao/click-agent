"""Wythoff's game: decide and give the lexicographically smallest winning move.

stdin:
    line 1: a b     (1<=a,b<=25)

Moves: (i) remove any positive number from one pile, or
       (ii) remove the same positive number from both piles.
Player taking the last stone wins.

stdout:
    "LOSE"      if the position is a cold (P-)position, else
    "WIN i j"   with i stones removed from pile 1, j from pile 2,
                minimising (i, j) lexicographically among all winning moves.

Cold positions are computed by exact DP over the whole input domain
(0..MAX), so no floating point / floor-sqrt approximation is involved.
"""

MAX = 30  # covers the stated input domain 1..25 with margin


def _build_cold_table(limit=MAX):
    """cold[a][b] is True iff (a, b) is a losing (P-)position.

    Recurrence: (a,b) is cold iff it is (0,0) or every legal move leads to a
    non-cold position; we build it with the equivalent incremental rule.
    """
    cold = [[False] * (limit + 1) for _ in range(limit + 1)]
    for a in range(limit + 1):
        for b in range(limit + 1):
            if a == 0 and b == 0:
                cold[a][b] = True
                continue
            winning = False
            for i in range(0, a + 1):
                for j in range(0, b + 1):
                    if i == 0 and j == 0:
                        continue
                    if i == 0 or j == 0 or i == j:  # legal Wythoff move
                        if cold[a - i][b - j]:
                            winning = True
                            break
                if winning:
                    break
            cold[a][b] = not winning
    return cold


_COLD = _build_cold_table()


def _is_cold(a: int, b: int) -> bool:
    return _COLD[a][b]


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])

    if _is_cold(a, b):
        return "LOSE"

    # Enumerate candidate moves in lexicographic order and take the first win.
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue  # not a legal Wythoff move
            if _is_cold(a - i, b - j):
                return "WIN %d %d" % (i, j)
    raise AssertionError("unreachable: non-cold position without winning move")
