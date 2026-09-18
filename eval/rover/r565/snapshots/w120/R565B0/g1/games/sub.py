"""Subtraction game: WIN m / LOSE."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    n, k = (int(x) for x in lines[idx].split())
    idx += 1
    s = [int(x) for x in lines[idx].split()]
    s = sorted(s[:k])
    win = [False] * (n + 1)
    for total in range(1, n + 1):
        for step in s:
            if step <= total and not win[total - step]:
                win[total] = True
                break
    if not win[n]:
        return "LOSE"
    for step in sorted(s):
        if step <= n and not win[n - step]:
            return "WIN " + str(step)
    return "LOSE"
