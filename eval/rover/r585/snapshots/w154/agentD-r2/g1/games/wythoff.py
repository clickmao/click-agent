def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    los = set()
    i = 0
    while True:
        p = (i * (1 + 5 ** 0.5)) // 2
        x = int(p)
        y = x + i
        if x > 50 and y > 50:
            break
        los.add((x, y))
        los.add((y, x))
        i += 1
    if (a, b) in los:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or i > a or j > b:
                continue
            na = a - i
            nb = b - j
            if (na, nb) in los and na >= 0 and nb >= 0:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
