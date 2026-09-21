def solve(text: str) -> str:
    a, b = map(int, text.split())
    # Wythoff P-positions: (floor(n*phi), floor(n*phi^2))
    phi = (1 + 5 ** 0.5) / 2
    for n in range(0, 26):
        p = int(n * phi)
        q = int(n * phi * phi)
        if (p, q) == (a, b) or (q, p) == (a, b):
            return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if (i == j) or (i == 0) or (j == 0):
                # legal move; check if resulting position is a P-position
                is_p = False
                for n in range(0, 26):
                    p = int(n * phi)
                    q = int(n * phi * phi)
                    if (p, q) == (na, nb) or (q, p) == (na, nb):
                        is_p = True
                        break
                if is_p:
                    best = (i, j)
                    break
        if best:
            break
    return "WIN %d %d" % best
