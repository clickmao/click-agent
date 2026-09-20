def solve(text):
    lines = [l for l in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    a, b = map(int, lines[0].split())
    LIM = 30
    losing = set()
    i = 0
    while True:
        ai = (i * (1 + 5 ** 0.5)) // 2
        bi = ai + i
        ai = int(ai + 0.5)
        bi = int(bi + 0.5)
        if ai > LIM or bi > LIM:
            break
        losing.add((ai, bi))
        losing.add((bi, ai))
        i += 1
    if (a, b) in losing:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in losing:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
