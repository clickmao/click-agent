"""Wythoff's game: report the lexicographically-first winning move."""


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    def is_losing(x: int, y: int) -> bool:
        lo, hi = (x, y) if x <= y else (y, x)
        return lo == (hi - lo) * (1 + 5 ** 0.5) // 2

    if is_losing(a, b):
        return "LOSE"

    for i in range(0, a + 1):
        if is_losing(a - i, b):
            return "WIN " + str(i) + " 0"
    for j in range(0, b + 1):
        if is_losing(a, b - j):
            return "WIN 0 " + str(j)
    for t in range(1, min(a, b) + 1):
        if is_losing(a - t, b - t):
            return "WIN " + str(t) + " " + str(t)
    return "LOSE"
