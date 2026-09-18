def solve(text):
    a, b = map(int, text.split()[:2])
    LIM = 30
    bad = set()
    for a1 in range(LIM + 1):
        for b1 in range(LIM + 1):
            ok = False
            for i in range(1, a1 + 1):
                if (a1 - i, b1) in bad:
                    ok = True
                    break
            if not ok:
                for j in range(1, b1 + 1):
                    if (a1, b1 - j) in bad:
                        ok = True
                        break
            if not ok:
                for d in range(1, min(a1, b1) + 1):
                    if (a1 - d, b1 - d) in bad:
                        ok = True
                        break
            if not ok:
                bad.add((a1, b1))

    def is_bad(x, y):
        return (x, y) in bad

    if is_bad(a, b):
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if is_bad(na, nb):
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
