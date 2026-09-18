from functools import lru_cache

LIMIT = 25


@lru_cache(maxsize=None)
def _losing(a: int, b: int) -> bool:
    for i in range(1, a + 1):
        if _losing(a - i, b):
            return False
    for j in range(1, b + 1):
        if _losing(a, b - j):
            return False
    for t in range(1, min(a, b) + 1):
        if _losing(a - t, b - t):
            return False
    return True


def solve(text: str) -> str:
    a, b = map(int, text.split())
    if _losing(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _losing(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    return 'WIN %d %d' % best
