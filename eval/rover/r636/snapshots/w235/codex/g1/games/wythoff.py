from functools import lru_cache


@lru_cache(maxsize=None)
def _losing(x: int, y: int) -> bool:
    if x == 0 and y == 0:
        return True
    for t in range(1, x + 1):
        if _losing(x - t, y):
            return False
    for t in range(1, y + 1):
        if _losing(x, y - t):
            return False
    for t in range(1, min(x, y) + 1):
        if _losing(x - t, y - t):
            return False
    return True


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    if _losing(a, b):
        return "LOSE"

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j == 0:
                nx, ny = a - i, b
            elif i == 0 and j > 0:
                nx, ny = a, b - j
            else:
                nx, ny = a - i, b - j
            if _losing(nx, ny):
                return "WIN %d %d" % (i, j)
    return "LOSE"
