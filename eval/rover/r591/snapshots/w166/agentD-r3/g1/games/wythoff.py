def solve(text):
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())
    losing = set()
    for n in range(50):
        x = (n * (1 + 5 ** 0.5) / 2)
        x = int(x)
        if x * 0 + x > 60:
            break
        y = x + n
        losing.add((x, y))
        losing.add((y, x))
    if (a, b) in losing:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            na = a - i
            nb = b - j
            if i > 0 and j > 0 and i != j:
                continue
            if (na, nb) in losing:
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
