def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())
    LOSE = set()
    i, j = 0, 0
    while i <= 25 and j <= 25:
        LOSE.add((i, j))
        i, j = i + 1, j + 2
    if (a, b) in LOSE:
        return 'LOSE'
    best = None
    for da in range(0, a + 1):
        for db in range(0, b + 1):
            if da == 0 and db == 0:
                continue
            na, nb = a - da, b - db
            if da > 0 and db > 0 and da != db:
                continue
            if (na, nb) in LOSE:
                if best is None or (da, db) < best:
                    best = (da, db)
    if best is None:
        return 'LOSE'
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
