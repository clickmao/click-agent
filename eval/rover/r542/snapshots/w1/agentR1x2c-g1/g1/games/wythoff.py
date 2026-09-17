def solve(text: str) -> str:
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    a, b = map(int, lines[i].split()[:2])
    if a > b:
        a, b = b, a
    size = 26
    lose = set()
    seen = set()
    for n in range(0, size * 2):
        cand = 0
        while (cand, cand + n) in seen or cand in seen or (cand + n) in seen:
            cand += 1
        lose.add((cand, cand + n))
        seen.add(cand)
        seen.add(cand + n)
    for x, y in lose:
        if x == a and y == b:
            return 'LOSE'
    best = None
    for i2 in range(0, a + 1):
        for j2 in range(0, b + 1):
            if i2 == 0 and j2 == 0:
                continue
            if i2 != 0 and j2 != 0 and i2 != j2:
                continue
            if a - i2 > b - j2:
                continue
            if (a - i2, b - j2) in lose:
                best = (i2, j2)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
