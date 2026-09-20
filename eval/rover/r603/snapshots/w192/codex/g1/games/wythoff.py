from functools import lru_cache


@lru_cache(maxsize=None)
def _losing(x: int, y: int) -> bool:
    if x == 0 and y == 0:
        return True
    for i in range(0, x + 1):
        for j in range(0, y + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _losing(x - i, y - j):
                return False
    return True


def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])
    if _losing(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
