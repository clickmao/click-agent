def solve(text: str) -> str:
    a, b = (int(x) for x in text.split())

    pairs = []
    used_a = set()
    used_b = set()
    n = 0
    while True:
        x = min(v for v in range(0, 80) if v not in used_a and v not in used_b)
        y = x + n
        pairs.append((x, y))
        used_a.add(x)
        used_b.add(y)
        n += 1
        if x > 25 and y > 25:
            break
    cold = set(pairs)

    def losing(u, v):
        lo, hi = (u, v) if u <= v else (v, u)
        return (lo, hi) in cold

    if losing(a, b):
        return "LOSE"

    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or i > a or j > b:
                continue
            if losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
