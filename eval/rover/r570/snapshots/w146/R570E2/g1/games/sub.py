"""Subtraction game: win/lose and smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ""
    n, k = (int(x) for x in lines[0].split())
    steps = sorted(int(x) for x in lines[1].split())
    steps = [s for s in steps if 1 <= s <= n] if n >= 1 else []
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in steps:
            if s <= m and not win[m - s]:
                win[m] = True
                break
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
