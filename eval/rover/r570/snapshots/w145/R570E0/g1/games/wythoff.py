def _lose(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    aa = int(d * (1 + 5 ** 0.5) / 2)
    return a == aa


def solve(text: str) -> str:
    a, b = map(int, text.split())
    if _lose(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not ((i == 0) or (j == 0) or (i == j)):
                continue
            if _lose(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
