def is_losing(a, b):
    x = min(a, b)
    y = max(a, b)
    # losing positions are (floor(n*phi), floor(n*phi)+n)
    n = y - x
    if n < 0:
        return False
    phi = (1 + 5 ** 0.5) / 2
    return x == int(n * phi)


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    if is_losing(a, b):
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN " + str(best[0]) + " " + str(best[1])
