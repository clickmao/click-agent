"""Wythoff game: lexicographically smallest winning move."""


def _losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    for j in range(1, 26):
        p = (j * (1 + 5 ** 0.5) / 2)
        x = int(p) if int(p) < p else int(p) - 1
        if x > 25:
            break
        if a == x and b == x + j:
            return True
    return False


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
