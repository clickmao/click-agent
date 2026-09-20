def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    phi = (1 + 5 ** 0.5) / 2
    lose = set()
    t = 0
    while True:
        p = int(t * phi)
        q = p + t
        if p > 25 and q > 25:
            break
        lose.add((p, q))
        lose.add((q, p))
        t += 1
    if (a, b) in lose:
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i and j and i != j:
                continue
            if (a - i, b - j) in lose:
                return "WIN %d %d" % (i, j)
