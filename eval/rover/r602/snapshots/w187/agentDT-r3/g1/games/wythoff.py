LIM = 25
P = set()
seen = set()
for t in range(0, LIM + 1):
    m = t
    while (m, m + t) in seen or m > LIM:
        m += 1
    if m > LIM:
        continue
    seen.add((m, m + t))
    seen.add((m + t, m))
    P.add((m, m + t))
    P.add((m + t, m))


def solve(text):
    a, b = map(int, text.split())
    if (a, b) in P:
        return 'LOSE'
    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != j and i != 0 and j != 0:
                continue
            if (a - i, b - j) in P:
                cands.append((i, j))
    cands.sort()
    i, j = cands[0]
    return 'WIN ' + str(i) + ' ' + str(j)
