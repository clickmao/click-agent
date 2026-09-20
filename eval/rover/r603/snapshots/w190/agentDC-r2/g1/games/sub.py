"""Subtraction game: win/lose and smallest winning first move."""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split()[:2])
    steps = sorted(int(x) for x in lines[1].split()[:k])
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in steps)
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
