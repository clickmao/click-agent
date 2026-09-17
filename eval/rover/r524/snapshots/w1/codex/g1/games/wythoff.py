def solve(text: str) -> str:
    tokens = text.split()
    if not tokens:
        return ""
    a, b = int(tokens[0]), int(tokens[1])
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na >= 0 and nb >= 0 and losing(na, nb):
                return "WIN " + str(i) + " " + str(j)
    return "LOSE"


def losing(a: int, b: int) -> bool:
    lo, hi = (a, b) if a <= b else (b, a)
    d = hi - lo
    t = (d * (1 + 5 ** 0.5) / 2)
    import math
    tt = int(math.floor(t + 1e-9))
    if tt < 0:
        return False
    lo_t = tt
    hi_t = tt + d
    return lo == lo_t and hi == hi_t
