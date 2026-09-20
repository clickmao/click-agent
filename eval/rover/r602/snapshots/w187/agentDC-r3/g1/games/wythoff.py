def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])
    LIM = 30
    lose = set()
    for x in range(LIM + 1):
        for y in range(x, LIM + 1):
            ok = True
            for (u, v) in lose:
                if u == x or v == y or (v - u) == (y - x):
                    ok = False
                    break
            if ok:
                lose.add((x, y))
    is_lose = (min(a, b), max(a, b)) in lose
    if is_lose:
        return 'LOSE'
    best = None
    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i > 0 and j > 0 and i == j:
                pass
            elif i > 0 and j != 0:
                continue
            elif j > 0 and i != 0:
                continue
            moves.append((i, j))
    candidates = []
    for (i, j) in moves:
        na, nb = a - i, b - j
        if (min(na, nb), max(na, nb)) in lose:
            candidates.append((i, j))
    candidates.sort()
    best = candidates[0]
    return 'WIN ' + str(best[0]) + ' ' + str(best[1])
