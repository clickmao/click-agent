PHI = (1 + 5 ** 0.5) / 2


def is_losing(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    p = int(d * PHI)
    return a == p and b == p + d


def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if is_losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
