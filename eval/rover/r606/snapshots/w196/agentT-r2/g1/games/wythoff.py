def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])
    N = max(a, b) + 1
    cold = []
    for x in range(0, N):
        for y in range(x, N):
            ok = True
            for (cx, cy) in cold:
                if cx == x or cy == y or (x - cx) == (y - cy):
                    ok = False
                    break
            if ok:
                cold.append((x, y))
                break
    moves = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            na, nb = a - i, b - j
            if na > nb:
                na, nb = nb, na
            if (na, nb) in cold:
                moves.append((i, j))
    if (min(a, b), max(a, b)) in cold:
        return "LOSE"
    moves.sort()
    i, j = moves[0]
    return "WIN " + str(i) + " " + str(j)
