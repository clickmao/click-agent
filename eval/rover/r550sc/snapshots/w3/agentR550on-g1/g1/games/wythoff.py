def _cold(a, b):
    if a > b:
        a, b = b, a
    t = b - a
    x = (t * (1 + 5 ** 0.5) / 2) // 1
    c = int(x + 1e-9)
    while c * (1 + 5 ** 0.5) / 2 // 1 < t:
        c += 1
    while c * (1 + 5 ** 0.5) / 2 // 1 > t and c > 0:
        c -= 1
    return (c, c + t)


def _lose(a, b):
    ca, cb = _cold(a, b)
    return ca == a and cb == b


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())
    if _lose(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0:
                if _lose(a, b - j):
                    best = (i, j)
                    break
            elif j == 0:
                if _lose(a - i, b):
                    best = (i, j)
                    break
            elif i == j:
                if _lose(a - i, b - i):
                    best = (i, j)
                    break
        if best is not None:
            break
    return 'WIN %d %d' % best
