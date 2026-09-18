"""Wythoff game: LOSE / WIN i j (lexicographically smallest winning move)."""


def _lose(a, b):
    x, y = (a, b) if a <= b else (b, a)
    d = y - x
    t = (5 ** 0.5 + 1) / 2
    xr = int(d * t)
    for cand in (xr - 1, xr, xr + 1):
        if cand < 0:
            continue
        if cand == x and cand + d == y:
            return True
    return False


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    a, b = (int(x) for x in lines[idx].split())
    if _lose(a, b):
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if _lose(a - i, b - j):
                return "WIN " + str(i) + " " + str(j)
    return "LOSE"
