def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())
    n = max(a, b)
    lose = set()
    used = {0}
    for i in range(1, n + 1):
        if i in used:
            continue
        j = i + 1
        while j in used:
            j += 1
        used.add(i)
        used.add(j)
        lose.add((i, j))
        lose.add((j, i))
    if (a, b) in lose:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if (a - i, b - j) in lose:
                if best is None or (i, j) < best:
                    best = (i, j)
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
