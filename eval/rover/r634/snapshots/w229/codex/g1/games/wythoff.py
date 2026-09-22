from math import floor


def _is_losing(a, b):
    lo, hi = (a, b) if a < b else (b, a)
    return lo == floor((hi - lo) * (1 + 5 ** 0.5) / 2)


def solve(text):
    a, b = map(int, text.split())
    if _is_losing(a, b):
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if _is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
