def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())
    x, y = min(a, b), max(a, b)
    moves = []
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0:
                moves.append((i, j))
            elif i > 0 and j == 0:
                moves.append((i, 0))
            else:
                moves.append((0, j))
    moves.sort()
    import math
    for (i, j) in moves:
        na = a - i
        nb = b - j
        nx, ny = min(na, nb), max(na, nb)
        t = ny - nx
        if ny == int(math.floor(t * (1 + math.sqrt(5)) / 2)) and nx == int(math.floor(t * (1 + math.sqrt(5)) / 2)) + t:
            pass
        if nx == int(math.floor(t * (1 + math.sqrt(5)) / 2)) and t == ny - nx:
            return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
