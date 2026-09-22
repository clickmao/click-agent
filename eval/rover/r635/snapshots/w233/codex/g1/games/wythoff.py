def solve(text: str) -> str:
    data = text.split()
    a, b = int(data[0]), int(data[1])
    # Losing (cold) positions are (xm, ym) = (floor(m*phi), floor(m*phi^2))
    # with xm + m = ym.  Enumerate m by the "mex" characterization:
    # each positive integer appears as a coordinate exactly once.
    used = set()
    lose = set()
    m = 0
    while True:
        m += 1
        x = 1
        while x in used:
            x += 1
        if x > max(a, b):
            break
        y = x + m
        used.add(x)
        used.add(y)
        lose.add((x, y))
        lose.add((y, x))
    if (a, b) in lose:
        return "LOSE"
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in lose:
                best = (i, j)
                break
        if best:
            break
    i, j = best
    return "WIN %d %d" % (i, j)
