def solve(text: str) -> str:
    a, b = (int(t) for t in text.split())

    n = max(a, b)
    lose = set()
    for x in range(0, n + 1):
        for y in range(x, n + 1):
            moves = []
            for i in range(1, x + 1):
                moves.append((x - i, y))
            for j in range(1, y + 1):
                moves.append((x, y - j))
            for k in range(1, min(x, y) + 1):
                moves.append((x - k, y - k))
            is_lose = True
            for (nx, ny) in moves:
                if (min(nx, ny), max(nx, ny)) not in lose:
                    is_lose = False
                    break
            if is_lose:
                lose.add((x, y))

    if (a, b) in lose:
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            key = (min(na, nb), max(na, nb))
            if key in lose:
                return "WIN %d %d" % (i, j)
    return "WIN 0 0"
