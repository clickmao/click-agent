def solve(text: str) -> str:
    import math
    lines = [l for l in text.splitlines() if l.strip() != ""]
    a, b = map(int, lines[0].split()[:2])
    big = max(a, b) + 5
    phi = (1 + 5 ** 0.5) / 2
    losing = set()
    n = 0
    while True:
        p = int(math.floor(phi * n))
        q = p + n
        if p > big and q > big:
            break
        losing.add((p, q))
        losing.add((q, p))
        n += 1
    if (a, b) in losing:
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if (a - i, b - j) in losing:
                return "WIN %d %d" % (i, j)
    return "LOSE"
