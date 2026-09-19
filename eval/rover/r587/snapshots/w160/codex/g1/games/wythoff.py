def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    def is_lose(x: int, y: int) -> bool:
        if x > y:
            x, y = y, x
        return x == int((y - x) * (1 + 5 ** 0.5) / 2)

    if is_lose(a, b):
        return 'LOSE'

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                if is_lose(a - i, b - j):
                    best = (i, j)
                    break
        if best is not None:
            break
    i, j = best
    return 'WIN %d %d' % (i, j)
