def solve(text: str) -> str:
    a, b = map(int, text.split())
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j):
                continue
            x, y = a - i, b - j
            if x > y:
                x, y = y, x
            t = int((y - x) * 1.618033988749895 // 1 + 0.5)
            if t < 0:
                t = 0
            ok = False
            for tt in (t - 1, t, t + 1):
                if tt >= 0 and x == int(tt * (1 + 5 ** 0.5) / 2) and y == x + tt:
                    ok = True
                    break
            if ok:
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
