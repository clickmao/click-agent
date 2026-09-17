"""Subtraction game: win/lose + smallest winning first move.
Pure function solve(text) -> str (no trailing newline).
"""


def _parse(text):
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    moves = [int(x) for x in lines[2:2 + k]]
    return n, moves


def solve(text: str) -> str:
    n, moves = _parse(text)
    # win[x] = True if player to move with x stones has a winning strategy.
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return "LOSE"
    best = min(s for s in moves if s <= n and not win[n - s])
    return "WIN %d" % best
