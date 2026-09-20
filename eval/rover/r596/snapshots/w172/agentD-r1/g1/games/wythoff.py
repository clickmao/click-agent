def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    x, y = min(a, b), max(a, b)

    losing = set()
    # losing pairs: (floor(t*phi), floor(t*phi^2)), t >= 0
    t = 0
    while True:
        p = (t * 1618033989) // 1000000000
        q = (t * 2618033989) // 1000000000
        if p <= 25 and q <= 25:
            losing.add((p, q))
            losing.add((q, p))
            t += 1
        else:
            break

    if (x, y) in losing:
        return 'LOSE'

    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ok = False
            if i > 0 and j == 0:
                ok = True
            elif i == 0 and j > 0:
                ok = True
            elif i == j and i > 0:
                ok = True
            if ok and (min(a - i, b - j), max(a - i, b - j)) in losing:
                moves.append((i, j))
    moves.sort()
    i, j = moves[0]
    return 'WIN ' + str(i) + ' ' + str(j)
