def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    count = min(a, b)
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i == j and i <= count) or (i == 0) or (j == 0):
                if is_lose(a - i, b - j):
                    return 'WIN %d %d' % (i, j)
    return 'LOSE'


def is_lose(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    seen = set()
    pairs = []
    n = 0
    while True:
        p = (int(n * 1.618033988749895) + n, int(n * 1.618033988749895) + 2 * n)
        if p[0] > 25 or p[1] > 25:
            break
        pairs.append(p)
        n += 1
    return (a, b) in pairs
