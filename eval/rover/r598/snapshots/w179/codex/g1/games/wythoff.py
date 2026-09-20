def solve(text: str) -> str:
    a, b = (int(v) for v in text.split()[:2])
    lose = set()
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if (i, j) in lose:
                continue
            # determine if (i,j) is a losing position by checking moves
            ok = True
            # reduce first pile
            if any((i - d, j) in lose for d in range(1, i + 1)):
                ok = False
            if ok and any((i, j - d) in lose for d in range(1, j + 1)):
                ok = False
            if ok and any((i - d, j - d) in lose for d in range(1, min(i, j) + 1)):
                ok = False
            if ok:
                lose.add((i, j))
    if (a, b) in lose:
        return 'LOSE'
    best = None
    for da in range(0, a + 1):
        for db in range(0, b + 1):
            if da == 0 and db == 0:
                continue
            if da > 0 and db > 0 and da != db:
                continue
            if (a - da, b - db) in lose:
                best = (da, db)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
