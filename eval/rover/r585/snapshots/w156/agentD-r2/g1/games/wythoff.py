"""Wythoff's game: two piles a b; move: remove any positive amount from one pile,
or the same positive amount from both piles. Taking the last stone wins.

solve(text) returns "LOSE" for losing positions, otherwise "WIN i j" for the
lexicographically smallest winning move (compare i then j; i,j >= 0, not both 0).

Losing positions are exactly the cold positions floor(n*phi), floor(n*phi^2).
The two smallest winning moves, checked in lexicographic order, are:
  1) reduce one pile to its cold partner (covers (i,j) with a zero component);
  2) equal removal from both piles onto a cold pair (smallest such i).
"""


def solve(text: str) -> str:
    head = text.split()
    if not head:
        return "LOSE"
    a, b = int(head[0]), int(head[1])
    x, y = (a, b) if a <= b else (b, a)

    # Cold positions as a mapping from one coordinate to the other.
    partners = {}
    p, q = 0, 0
    while p <= 25 and q <= 25:
        partners[p] = q
        partners[q] = p
        p = p + q + 1
        q = p + 1

    if partners.get(x, -1) == y:
        return "LOSE"

    # Candidate 1: remove 0 or more stones from just one pile.  The pair can
    # always be repaired this way since any non-cold pair has a coordinate whose
    # cold partner is smaller.
    for k in (x, y):
        if k in partners and partners[k] < k:
            t = partners[k]
            if a == k:
                return "WIN %d 0" % (a - t)
            return "WIN 0 %d" % (b - t)

    # Candidate 2: equal removal from both piles onto a cold pair d, d'.
    if x == y:
        return "WIN %d %d" % (x, y)
    for d in range(x):
        d2 = d + x + y - 2 * d
        if d + d2 == x + y and partners.get(d, -1) == d2:
            return "WIN %d %d" % (x - d, y - d)
    return "LOSE"
