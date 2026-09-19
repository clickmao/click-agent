def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    def is_lose(pa, pb):
        lo, hi = min(pa, pb), max(pa, pb)
        d = hi - lo
        phi = (1 + 5 ** 0.5) / 2
        t = int(d * phi)
        if (t, t + d) == (lo, hi):
            return True
        t += 1
        return (t, t + d) == (lo, hi)

    if is_lose(a, b):
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if is_lose(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
