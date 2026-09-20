def solve(text):
    parts = text.split()
    a = int(parts[0])
    b = int(parts[1])

    # Precompute losing (cold) positions: (a, b) with a <= b are Wythoff pairs
    # (floor(n*phi), floor(n*phi^2)).  A position is losing iff it is such a pair.
    LIM = 30
    phi = (1 + 5 ** 0.5) / 2
    cold = set()
    n = 0
    while True:
        x = int((n * phi) // 1) if False else int(n * phi)
        y = int(n * phi * phi)
        if x > LIM and y > LIM:
            break
        cold.add((x, y))
        n += 1
        if n > 200:
            break

    p, q = (a, b) if a <= b else (b, a)
    if (p, q) in cold:
        return 'LOSE'

    def is_cold(x, y):
        if x <= 0 or y <= 0:
            return x == 0 and y == 0
        u, v = (x, y) if x <= y else (y, x)
        return (u, v) in cold

    # all moves, collect (i, j) taking from pile1 and pile2, lexicographically smallest
    cands = []
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if is_cold(a - i, b - j):
                cands.append((i, j))
    cands.sort()
    i, j = cands[0]
    return 'WIN %d %d' % (i, j)
