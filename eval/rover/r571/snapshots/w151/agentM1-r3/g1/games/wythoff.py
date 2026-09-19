def _lose(a, b):
    seen = 0
    pairs = []
    need = max(a, b)
    n = 0
    while len(pairs) < 40:
        x = n * 3 // 2 + n % 2
        while True:
            y = x + n
            if all(x not in p and y not in p for p in pairs):
                break
            x += 1
        pairs.append((x, y))
        n += 1
        if x > need and y > need:
            break
    return (min(a, b), max(a, b)) in [(p[0], p[1]) for p in pairs]


def solve(text):
    a, b = (int(x) for x in text.split()[:2])
    if _lose(a, b):
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if (i == 0 or j == 0 or i == j) and _lose(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
