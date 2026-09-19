def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    for i in range(a, -1, -1):
        for j in range(b, -1, -1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j):
                x, y = a - i, b - j
                if (x, y) != (a, b):
                    pass
    cands = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            x, y = a - i, b - j
            if x < 0 or y < 0:
                continue
            if (i == 0 and j > 0) or (j == 0 and i > 0) or (i == j):
                if is_lose(x, y):
                    return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'


def is_lose(x, y):
    if x > y:
        x, y = y, x
    for k in range(0, 26):
        p = int(k * (1 + 5 ** 0.5) / 2)
        q = p + k
        if p == x and q == y:
            return True
        if p > x:
            break
    return False
