"""Wythoff's game: losing position test and lexicographically smallest winning move."""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    a, b = (int(v) for v in lines[idx].split()[:2])

    def losing(x, y):
        lo, hi = min(x, y), max(x, y)
        return lo == int((hi - lo) * (1 + 5 ** 0.5) / 2 + 0.5)

    if losing(a, b):
        return "LOSE"

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
