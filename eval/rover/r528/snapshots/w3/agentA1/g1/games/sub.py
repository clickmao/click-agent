"""Subtraction game: last stone taken wins.

solve(text) -> str : returns "WIN m" (smallest winning move) or "LOSE".
"""


def solve(text: str) -> str:
    toks = text.split()
    n = int(toks[0])
    k = int(toks[1])
    moves = sorted({int(x) for x in toks[2:2 + k]})

    # win[i] = True if position with i stones is winning for player to move.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        w = False
        for s in moves:
            if s <= i and not win[i - s]:
                w = True
                break
        win[i] = w

    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
