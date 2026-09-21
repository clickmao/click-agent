"""Wythoff's game: win/lose and lexicographically smallest winning move."""


def solve(text: str) -> str:
    lines = text.split()
    a = int(lines[0])
    b = int(lines[1])
    # losing positions: (floor(k*phi), floor(k*phi^2))
    PHI = (1 + 5 ** 0.5) / 2
    losing = set()
    k = 0
    while True:
        x = int(k * PHI) + k  # floor(k*phi^2) == floor(k*phi) + k
        y = int(k * PHI)
        if x > 25 and y > 25:
            break
        losing.add((y, x))
        losing.add((x, y))
        k += 1
        if k > 1000:
            break
    if (a, b) in losing:
        return "LOSE"
    best = None
    # moves type (i): remove from one pile
    for i in range(1, a + 1):
        cand = (i, 0)
        if (a - i, b) in losing:
            if best is None or cand < best:
                best = cand
    for j in range(1, b + 1):
        cand = (0, j)
        if (a, b - j) in losing:
            if best is None or cand < best:
                best = cand
    # moves type (ii): remove same positive from both
    for t in range(1, min(a, b) + 1):
        cand = (t, t)
        if (a - t, b - t) in losing:
            if best is None or cand < best:
                best = cand
    if best is None:
        return "LOSE"
    return "WIN {} {}".format(best[0], best[1])
