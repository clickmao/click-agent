def solve(text):
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    lose = set()
    r = 0
    while True:
        p = (r * (1 + 5 ** 0.5)) / 2
        x = int(p)
        y = x + r
        if x > max(a, b) or y > max(a, b):
            break
        lose.add((x, y))
        lose.add((y, x))
        r += 1
    if (a, b) in lose:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0) and i != j:
                continue
            if i > a or j > b:
                continue
            if i == a and j == b:
                continue
            na = a - i
            nb = b - j
            if na < 0 or nb < 0:
                continue
            if (na, nb) in lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
