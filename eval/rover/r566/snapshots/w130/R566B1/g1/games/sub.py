"""Subtraction game: first player win/lose and the smallest winning first move."""


def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip()]
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())
    assert len(moves) == k
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        win[m] = any(m >= s and not win[m - s] for s in moves)
    if not win[n]:
        return "LOSE"
    for s in moves:
        if n >= s and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
