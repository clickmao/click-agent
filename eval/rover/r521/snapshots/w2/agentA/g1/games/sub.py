"""Subtraction game: last stone taken wins.

stdin:
    line 1: n k        (1<=n<=80 stones, 1<=k<=12 moves)
    line 2: k distinct integers s1..sk (1<=si<=12, contains 1)

Move: remove exactly one allowed amount. Player taking the last stone wins.

stdout:
    "WIN m"  (m = smallest winning first move), or
    "LOSE"   (first player loses)
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())
    assert len(moves) == k

    # win[i] = True iff i stones is a winning position for the player to move.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    raise AssertionError("unreachable: winning position without winning move")
