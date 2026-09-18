def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())
    if a > b:
        a, b = b, a
    losing = set()
    for k in range(1, 26):
        ak = (k * (1 + 5 ** 0.5)) // 2
        bk = ak + k
        if ak > 25 or bk > 25:
            break
        losing.add((int(ak), int(bk)))
    if (a, b) in losing:
        return 'LOSE'
    limited = set()
    for _ in range(4):
        adiff = a - b
        for k in range(1, 26):
            ak = (k * (1 + 5 ** 0.5)) // 2
            bk = ak + k
            if ak > 25 or bk > 25:
                break
            limited.add((int(ak), int(bk)))
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na > nb:
                na, nb = nb, na
            if (na, nb) in losing:
                if best is None:
                    best = (i, j)
                break
        if best is not None:
            break
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            na, nb = a - i, b - j
            if na > nb:
                na, nb = nb, na
            if (na, nb) in losing:
                if (i, j) < best:
                    best = (i, j)
    return 'WIN %d %d' % best
