def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    def losing(x: int, y: int) -> bool:
        if x > y:
            x, y = y, x
        # Beatty sequences: losing positions are (floor(n*phi), floor(n*phi^2))
        # Check via characteristic: x == ((y - x) * (1 + 5 ** 0.5) / 2) rounded
        d = y - x
        cand = int(d * (1 + 5 ** 0.5) / 2 + 0.5)
        return x == cand

    if losing(a, b):
        return "LOSE"
    best = None
    # option (i): remove from one pile only
    for ni in range(0, a + 1):
        for nj in range(0, b + 1):
            if ni == 0 and nj == 0:
                continue
            if ni > 0 and nj > 0 and ni != nj:
                continue
            if losing(a - ni, b - nj):
                if best is None or (ni, nj) < best:
                    best = (ni, nj)
    return "WIN %d %d" % best
