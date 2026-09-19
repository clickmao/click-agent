import math


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    a, b = map(int, lines[idx].split()[:2])

    def losing(x, y):
        if x > y:
            x, y = y, x
        n = y - x
        return x == (n * (1 + math.isqrt(5))) // 2

    if losing(a, b):
        return "LOSE"
    phi_num = 1 + math.isqrt(5)
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or (i > 0 and j > 0) or (i == 0 or j == 0):
                if i > 0 and j > 0 and i != j:
                    continue
                na, nb_ = a - i, b - j
                if losing(na, nb_):
                    if best is None or (i, j) < best:
                        best = (i, j)
    return "WIN %d %d" % best
