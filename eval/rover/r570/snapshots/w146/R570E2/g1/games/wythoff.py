"""Wythoff game: losing positions and lexicographically smallest winning move."""


def _losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    return a == int((b - a) * (1 + 5 ** 0.5) / 2)


def solve(text: str) -> str:
    parts = text.split()
    if not parts:
        return ""
    a, b = int(parts[0]), int(parts[1])
    if _losing(a, b):
        return "LOSE"
    cands = []
    for i in range(1, a + 1):
        if _losing(a - i, b):
            cands.append((i, 0))
    for j in range(1, b + 1):
        if _losing(a, b - j):
            cands.append((0, j))
    for t in range(1, min(a, b) + 1):
        if _losing(a - t, b - t):
            cands.append((t, t))
    i, j = min(cands)
    return "WIN " + str(i) + " " + str(j)
