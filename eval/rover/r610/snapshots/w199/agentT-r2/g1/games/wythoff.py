def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    n = 25
    lose = set()
    for i in range(n + 1):
        for j in range(i, n + 1):
            if (i, j) in lose:
                continue
            ok = False
            for x in range(i):
                if (x, j) in lose:
                    ok = True
                    break
            if not ok:
                for y in range(j):
                    if (i, y) in lose or (y, i) in lose:
                        ok = True
                        break
            if not ok:
                d = j - i
                for t in range(i):
                    if (t, t + d) in lose:
                        ok = True
                        break
            if not ok:
                lose.add((i, j))
                lose.add((j, i))
    if (a, b) in lose:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or (i > a) or (j > b):
                continue
            if (a - i, b - j) in lose:
                return 'WIN %d %d' % (i, j)
