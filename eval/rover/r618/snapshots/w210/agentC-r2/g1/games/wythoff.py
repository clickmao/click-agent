LIMIT = 64


def _lose_table():
    lose = {}
    used = set()
    k = 0
    while k <= LIMIT:
        a = int(k * 1.618033988749895) + 1
        while a in used or (a + k) in used:
            a += 1
        b = a + k
        if b > 2 * LIMIT:
            break
        lose[(a, b)] = True
        lose[(b, a)] = True
        used.add(a)
        used.add(b)
        k += 1
    return lose


_TABLE = _lose_table()


def is_lose(a, b):
    return _TABLE.get((a, b), False)


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    if is_lose(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if is_lose(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
