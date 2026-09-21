"""Subtraction game: two players alternately remove one of the allowed
counts from a single pile; the player taking the last stone wins.

solve(text) parses:
  line 1: n k  (n stones; k distinct allowed moves)
  line 2: s1 .. sk (each >= 1, includes 1)
Returns 'WIN m' (m = numerically smallest winning first move) when the
first player wins, else 'LOSE'. No trailing newline.
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())[:k]
    # win[i] = True if the player to move wins with i stones left.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
