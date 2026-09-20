def losing(a, b):
    x, y = (a, b) if a <= b else (b, a)
    # 必败点 (x, y) 满足 x = floor(k*phi), y = x + k
    phi = (1 + 5 ** 0.5) / 2
    k = y - x
    if k < 0:
        return False
    return x == int(k * phi)


def solve(text):
    a, b = map(int, text.split()[:2])

    if losing(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or i > a or j > b:
                continue
            if losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
