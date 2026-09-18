"""Wythoff's game: losing-position test and lexicographically minimal move."""

PHI = (1 + 5.0 ** 0.5) / 2.0


def _cold(a, b):
    lo, hi = (a, b) if a <= b else (b, a)
    if lo == 0:
        return hi == 0
    n = hi - lo
    return lo == int(n * PHI)


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    a, b = map(int, lines[0].split()[:2])
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if _cold(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
