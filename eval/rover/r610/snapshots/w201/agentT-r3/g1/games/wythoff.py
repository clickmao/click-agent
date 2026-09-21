def _is_lose(a, b):
    x, y = (a, b) if a <= b else (b, a)
    return x == int(((y - x) * (1 + 5 ** 0.5) / 2.0))


def solve(text: str) -> str:
    a, b = map(int, text.split()[0:2])
    if _is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_lose(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
