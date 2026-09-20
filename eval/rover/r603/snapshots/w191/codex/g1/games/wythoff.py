def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    def losing(p, q):
        if p > q:
            p, q = q, p
        i = q - p
        # losing positions are (floor(i*phi), floor(i*phi)+i)
        phi = (1 + 5 ** 0.5) / 2
        return p == int(i * phi)

    if losing(a, b):
        return "LOSE"

    for i in range(0, a + 1):
        lo = 0 if i > 0 else 1
        for j in range(lo, b + 1):
            if i > a or j > b:
                continue
            na, nb = a - i, b - j
            if losing(na, nb):
                return "WIN %d %d" % (i, j)
    return "LOSE"
