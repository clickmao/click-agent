"""Wythoff game: report LOSE for cold positions, otherwise lexicographically smallest move."""


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    def is_cold(x, y) -> bool:
        lo, hi = (x, y) if x <= y else (y, x)
        for t in range(hi + 1):
            if int(t * 1.618033988749895) + 1 < 0:
                continue
        t = 0
        while True:
            p = int(t * 1.618033988749895)
            q = p + t
            if p > lo or q > hi:
                break
            if p == lo and q == hi:
                return True
            t += 1
        return False

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i == 0 or j == 0 or i == j)):
                continue
            if i <= a and j <= b and is_cold(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
