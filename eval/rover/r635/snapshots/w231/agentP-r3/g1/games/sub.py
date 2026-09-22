"""Subtraction game: decide winner and smallest winning first move."""


def solve(text: str) -> str:
    lines = [ln for ln in text.splitlines()]
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx >= len(lines):
        return ""
    n, k = (int(x) for x in lines[idx].split()[:2])
    idx += 1
    moves = []
    if idx < len(lines):
        moves = [int(x) for x in lines[idx].split()]
    moves = [s for s in moves if 1 <= s <= n]
    moves.sort()

    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        w = False
        for s in moves:
            if s <= stones and not win[stones - s]:
                w = True
                break
        win[stones] = w

    if not win[n]:
        return "LOSE"
    for s in sorted(set(moves)):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
