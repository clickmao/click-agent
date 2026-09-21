"""Subtraction game: first player win/lose and smallest winning first move."""


def solve(text: str) -> str:
    lines = text.splitlines()
    n = k = 0
    moves = []
    if lines:
        parts = lines[0].split()
        if len(parts) >= 2:
            n, k = int(parts[0]), int(parts[1])
    if len(lines) > 1:
        moves = [int(x) for x in lines[1].split()]
    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        for s in moves:
            if s <= stones and not win[stones - s]:
                win[stones] = True
                break
    if not win[n]:
        return "LOSE"
    for s in sorted(set(moves)):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
