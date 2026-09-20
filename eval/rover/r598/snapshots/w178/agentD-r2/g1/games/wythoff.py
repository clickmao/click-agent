def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])

    def is_lose(x, y):
        if x > y:
            x, y = y, x
        for i in range(x + 1):
            for j in range(y + 1):
                if i == 0 and j == 0:
                    continue
                if i == j and i <= x:
                    if is_lose_cached(x - i, y - i):
                        return False
                if i == 0:
                    if is_lose_cached(x, y - j):
                        return False
                if j == 0:
                    if is_lose_cached(x - i, y):
                        return False
        return True

    cache = {}

    def is_lose_cached(x, y):
        if x > y:
            x, y = y, x
        key = (x, y)
        if key in cache:
            return cache[key]
        m = min(x, y)
        # Wythoff losing positions: (floor(m*phi), floor(m*phi)+m)
        phi = (1 + 5 ** 0.5) / 2
        lose = False
        if x == int(m * phi) and y == x + m:
            lose = True
        cache[key] = lose
        return lose

    if is_lose_cached(a, b):
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            ni = a - i
            nj = b - j
            if is_lose_cached(ni, nj):
                best = (i, j)
                break
        if best is not None:
            break
    return "WIN " + str(best[0]) + " " + str(best[1])
