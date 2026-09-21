def solve(text):
    a, b = map(int, text.split()[:2])
    if a > b:
        a, b = b, a
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na > nb:
                na, nb = nb, na
            if na == int((nb - na) * (1 + 5 ** 0.5) / 2):
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
