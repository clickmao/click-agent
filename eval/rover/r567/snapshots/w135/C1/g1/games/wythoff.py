def is_lose(a, b):
    lo, hi = min(a, b), max(a, b)
    i = 0
    while True:
        p = (i * (1 + 5 ** 0.5)) // 2
        q = p + i
        if p > hi:
            return False
        if p == lo and q == hi:
            return True
        i += 1


def solve(text: str) -> str:
    a, b = map(int, text.split())
    if is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if is_lose(a - i, b - j):
                if best is None:
                    best = (i, j)
    return 'WIN %d %d' % best
