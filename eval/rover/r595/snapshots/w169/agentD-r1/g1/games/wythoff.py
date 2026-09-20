def _is_lose(a, b):
    i, j = 0, 0
    while True:
        if (i, j) == (a, b):
            return True
        if i > a or j > b:
            return False
        n = i + 1
        i, j = (int(n * (1 + 5 ** 0.5) / 2), int(n * (3 + 5 ** 0.5) / 2))


def solve(text):
    a, b = (int(x) for x in text.split()[:2])
    if _is_lose(a, b):
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and _is_lose(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break
    return "WIN " + str(best[0]) + " " + str(best[1])
