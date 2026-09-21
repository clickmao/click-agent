def solve(text: str) -> str:
    parts = text.split()
    a = int(parts[0])
    b = int(parts[1])

    def losing(x, y):
        return x == y == 0

    golden = (1 + 5 ** 0.5) / 2
    cold = set()
    for n in range(0, 30):
        i = int(n * golden)
        j = i + n
        cold.add((i, j))
        cold.add((j, i))
    if (a, b) in cold:
        return 'LOSE'
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na = a - i
            nb = b - j
            if na < 0 or nb < 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i == j:
                pass
            elif i > 0 and j == 0:
                pass
            elif i == 0 and j > 0:
                pass
            else:
                continue
            if (na, nb) in cold:
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
