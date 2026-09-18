def solve(text: str) -> str:
    a, b = map(int, text.split())

    # P-positions of Wythoff: (floor(n*phi), floor(n*phi)+n), n >= 0.
    # Store a lookup table (a,b <= 25 so positions small).
    losing = set()
    for n in range(0, 26):
        # compute floor(n*phi) exactly using an integer fixed-point method
        # phi = (1+sqrt5)/2; use rational convergent: Fibonacci ratios
        # Simpler: iterate continued fraction / use integer: floor(n*phi) can
        # be obtained by Beatty sequence: floor(n*(1+sqrt5)/2).
        x = int((n * (1 + 5 ** 0.5)) // 2)
        y = x + n
        losing.add((x, y))
        losing.add((y, x))

    if (a, b) in losing:
        return "LOSE"

    best = None
    # choose lexicographically smallest (i, j), i,j >= 0, not both 0
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in losing:
                best = (i, j)
                break
        if best is not None:
            break
    i, j = best
    return "WIN %d %d" % (i, j)
