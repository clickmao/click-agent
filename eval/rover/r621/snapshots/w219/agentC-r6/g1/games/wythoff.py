def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    LIM = 60
    phi = (1 + 5 ** 0.5) / 2
    losing = set()
    k = 0
    while True:
        p = int(k * phi)
        q = int(k * phi * phi)
        if p > LIM and q > LIM:
            break
        losing.add((p, q))
        k += 1
    lo, hi = (a, b) if a <= b else (b, a)
    if (lo, hi) in losing:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            valid = False
            if i == 0 or j == 0:
                valid = True
            elif i == j:
                valid = True
            if not valid:
                continue
            na, nb = a - i, b - j
            lo2, hi2 = (na, nb) if na <= nb else (nb, na)
            if (lo2, hi2) in losing:
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
