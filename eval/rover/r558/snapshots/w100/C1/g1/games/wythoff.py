def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    def losing(x, y):
        key = set()
        n = 0
        while True:
            px, py = (n * (1 + 5 ** 0.5) // 2, n * (3 + 5 ** 0.5) // 2)
            px, py = int(px), int(py)
            key.add((px, py))
            if px > x and py > y:
                break
            n += 1
        sx, sy = (x, y) if x <= y else (y, x)
        return (sx, sy) in key

    if losing(a, b):
        return "LOSE"

    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if (i == j) or (i == 0) or (j == 0):
                if losing(na, nb):
                    cand = (i, j)
                    if best is None or cand < best:
                        best = cand
    i, j = best
    return "WIN %d %d" % (i, j)
