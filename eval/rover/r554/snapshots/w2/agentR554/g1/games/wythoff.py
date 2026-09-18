def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    bad = set()
    m = max(a, b)
    for i in range(0, m + 1):
        for j in range(0, m + 1):
            if i == 0 and j == 0:
                continue
            k = i - j
            if k < 0 or k > m:
                continue
            x = j
            if x < m + 1:
                bad.add((x, x + k))
    n = max(a, b) + 1
    for i in range(0, n):
        for j in range(0, n):
            if i == 0 and j == 0:
                continue
            if a + b - i - j == 0:
                continue
            ok = False
            for ii in range(0, 26):
                for jj in range(0, 26):
                    if ii == 0 and jj == 0:
                        continue
                    if ii <= a and jj <= b and (ii or jj) and (a - ii, b - jj) in bad:
                        ok = True
                        break
                if ok:
                    break
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != j and i != 0 and j != 0:
                continue
            if (a - i, b - j) in bad:
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
