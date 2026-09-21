"""Wythoff game: remove from one heap any positive number, or the same
positive number from both heaps. The player taking the last stone wins.

stdin format:
    a b
Output: 'LOSE' if first player loses, else 'WIN i j' (lexicographically
smallest winning move, comparing i then j).
"""


def _is_lose(x, y):
    if x > y:
        x, y = y, x
    m = 0
    while True:
        p = m * 1618033988 // 1000000000
        q = p + m
        if p == x and q == y:
            return True
        if p > x:
            return False
        m += 1


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_lose(a, b):
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_lose(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
