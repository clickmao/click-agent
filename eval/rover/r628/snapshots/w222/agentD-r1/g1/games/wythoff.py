def solve(text):
    a, b = map(int, text.split())
    LIM = 32
    bad = set()
    for i in range(LIM):
        for j in range(LIM):
            if i == 0 and j == 0:
                continue
            cur = (i, j)
            found = False
            for x in range(1, i + 1):
                if (i - x, j) in bad:
                    found = True
                    break
            if not found:
                for y in range(1, j + 1):
                    if (i, j - y) in bad:
                        found = True
                        break
            if not found:
                for d in range(1, min(i, j) + 1):
                    if (i - d, j - d) in bad:
                        found = True
                        break
            if not found:
                bad.add(cur)
    if (a, b) in bad:
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i <= a and j <= b and (a - i, b - j) in bad:
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
