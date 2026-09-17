from functools import lru_cache


@lru_cache(maxsize=None)
def _lose(a, b):
    if a == 0 and b == 0:
        return True
    # single pile moves: (a,b) -> (a-di, b) or (a, b-dj)
    for di in range(1, a + 1):
        if _lose(a - di, b):
            return False
    for dj in range(1, b + 1):
        if _lose(a, b - dj):
            return False
    # both piles equal amounts
    for d in range(1, min(a, b) + 1):
        if _lose(a - d, b - d):
            return False
    return True


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if _lose(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _lose(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
