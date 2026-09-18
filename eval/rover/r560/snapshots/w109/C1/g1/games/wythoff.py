def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    x, y = min(a, b), max(a, b)
    losing = x == int((y - x) * ((5 ** 0.5 + 1) / 2))
    if losing:
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if i != j and i != 0 and j != 0:
                continue
            nx, ny = min(na, nb), max(na, nb)
            if nx == int((ny - nx) * ((5 ** 0.5 + 1) / 2)):
                return 'WIN %d %d' % (i, j)
