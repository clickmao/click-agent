def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    a, b = map(int, lines[idx].split())
    from functools import lru_cache

    @lru_cache(maxsize=None)
    def is_lose(x, y):
        if x == 0 and y == 0:
            return True
        for i in range(1, x + 1):
            if is_lose(x - i, y):
                return False
        for j in range(1, y + 1):
            if is_lose(x, y - j):
                return False
        for t in range(1, min(x, y) + 1):
            if is_lose(x - t, y - t):
                return False
        return True

    if is_lose(a, b):
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and is_lose(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
