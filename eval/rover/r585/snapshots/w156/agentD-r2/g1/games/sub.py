"""Subtraction game: n stones, moves given by a set s1..sk (always contains 1).

Players alternately remove exactly one of the allowed amounts; taking the last
stone wins. solve(text) returns "WIN m" with the smallest winning first move m
if the first player has a winning strategy, otherwise "LOSE". Winning positions
satisfy: win(x) is False iff every allowed move leads to a winning position for
the opponent. Pure win/loss DP suffices since only the smallest winning move is
needed.
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    if not lines:
        return "LOSE"
    head = lines[0].split()
    if not head:
        return "LOSE"
    n, k = (int(x) for x in head[:2])
    moves = []
    for line in lines[1:]:
        moves.extend(int(x) for x in line.split())
        if len(moves) >= k:
            break
    moves = sorted(m for m in moves[:k] if m >= 1)

    win = [False] * (n + 1)
    for x in range(1, n + 1):
        win[x] = any(m <= x and not win[x - m] for m in moves)

    if not win[n]:
        return "LOSE"
    for m in moves:
        if m <= n and not win[n - m]:
            return "WIN %d" % m
    return "LOSE"
