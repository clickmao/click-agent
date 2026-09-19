def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    phi = (1 + 5 ** 0.5) / 2
    seen = 0
    t = 0
    while True:
        x = int(t * phi) + t
        y = x + t
        if x > 25 or y > 25:
            break
        if (a, b) == (x, y) or (a, b) == (y, x):
            return "LOSE"
        t += 1
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            cand = sorted((na, nb))
            t = 0
            lose = False
            while True:
                x = int(t * phi) + t
                y = x + t
                if x > 25 or y > 25:
                    break
                if cand == [x, y]:
                    lose = True
                    break
                t += 1
            if lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
