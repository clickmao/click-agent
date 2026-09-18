"""Wythoff's game: losing-position test and lexicographically smallest winning move.

Input format:
    one line: a b   (1<=a<=25, 1<=b<=25)

A move either (i) removes any positive number from one pile, or (ii) removes the
same positive number from both piles; taking the last stone wins.
Output: `LOSE` when the position is a P-position for the player to move,
        else `WIN i j` with i stones from pile 1, j from pile 2, minimal in
        lexicographic order (i first, then j), i,j >= 0, not both zero.
"""


def _is_losing(a, b):
    a, b = min(a, b), max(a, b)
    d = b - a
    # P-positions: (floor(d*phi), floor(d*phi)+d) with phi = (1+sqrt(5))/2.
    x = (d * (1 + 5 ** 0.5)) / 2.0
    floor_x = int(x)
    if floor_x + 0.5 < x:
        floor_x += 1
    if floor_x - 1 >= 0:
        cands = (floor_x - 1, floor_x, floor_x + 1)
    else:
        cands = (floor_x, floor_x + 1)
    for c in cands:
        if c >= 0 and c + d == b and c == a:
            return True
    return False


def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])
    if _is_losing(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # (i, j) must be a legal move: one pile only, or both equally.
            if not (i == 0 or j == 0 or i == j):
                continue
            if _is_losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
