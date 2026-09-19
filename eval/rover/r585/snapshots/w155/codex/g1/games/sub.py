"""Subtraction game: report the smallest winning first move, or LOSE."""


def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = (int(v) for v in lines[0].split())
    moves = [int(v) for v in lines[1].split()][:k]
    win = [False] * (n + 1)
    for cur in range(1, n + 1):
        win[cur] = any(m <= cur and not win[cur - m] for m in moves)
    if not win[n]:
        return "LOSE"
    best = min(m for m in moves if m <= n and not win[n - m])
    return "WIN %d" % best
