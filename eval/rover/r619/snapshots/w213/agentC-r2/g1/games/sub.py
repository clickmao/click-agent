"""Subtraction game: first-player win/lose and smallest winning first move."""


def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    n, k = (int(x) for x in lines[idx].split()[:2])
    idx += 1
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    moves = [int(x) for x in lines[idx].split()[:k]]
    moves = sorted(m for m in moves if 1 <= m)
    win = [False] * (n + 1)
    for cur in range(1, n + 1):
        for m in moves:
            if m <= cur and not win[cur - m]:
                win[cur] = True
                break
    if not win[n]:
        return "LOSE"
    for m in moves:
        if m <= n and not win[n - m]:
            return "WIN %d" % m
    return "LOSE"
