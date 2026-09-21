def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])

    def losing(p, q):
        if p > q:
            p, q = q, p
        d = q - p
        p2 = (d * (1 + 5 ** 0.5)) // 2
        return p == int(p2)

    if losing(a, b):
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if losing(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break

    i, j = best
    return "WIN %d %d" % (i, j)
