"""Subtraction game: first player win/lose with the smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split()
    pos = 0
    n = int(lines[pos]); pos += 1
    k = int(lines[pos]); pos += 1
    steps = sorted(int(lines[pos + i]) for i in range(k))
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s > x:
                break
            if not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
