"""Subtraction game."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    n, k = (int(x) for x in lines[idx].split()[:2])
    moves = [int(x) for x in lines[idx + 1].split()[:k]]
    moves.sort()

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
