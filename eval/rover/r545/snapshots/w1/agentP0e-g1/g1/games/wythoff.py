def solve(text):
    a, b = map(int, text.split()[:2])
    x, y = (a, b) if a <= b else (b, a)
    k = y - x
    cold = ((k * (1 + 5 ** 0.5) / 2)).__int__()
    for kk in (int(k * 1.618033988749895), int(k * 1.618033988749895) + 1):
        if kk >= 0 and (kk, kk + k) == (x, y):
            return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            ni, nj = a - i, b - j
            if (i == j) or (i == 0) or (j == 0):
                sx, sy = (ni, nj) if ni <= nj else (nj, ni)
                kk2 = sy - sx
                c = int(kk2 * 1.618033988749895)
                if (c, c + kk2) == (sx, sy) or (c + 1, c + 1 + kk2) == (sx, sy):
                    return "WIN " + str(i) + " " + str(j)
    return "LOSE"
