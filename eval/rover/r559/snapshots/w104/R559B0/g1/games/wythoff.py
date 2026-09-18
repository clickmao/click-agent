def solve(text):
    a, b = map(int, text.split()[:2])
    phi = (5 ** 0.5 + 1) / 2
    diff = abs(a - b)
    t = int(diff / phi)
    for cand in (t, t + 1):
        if cand >= 0 and int(cand * phi) == min(a, b) and int(cand * phi) + cand == max(a, b):
            return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (i > 0 and j > 0 and i != j) or (i == 0 and j == 0):
                continue
            x, y = a - i, b - j
            d = abs(x - y)
            tt = int(d / phi)
            losing = False
            for cand in (tt, tt + 1):
                if cand >= 0 and int(cand * phi) == min(x, y) and int(cand * phi) + cand == max(x, y):
                    losing = True
            if losing:
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
