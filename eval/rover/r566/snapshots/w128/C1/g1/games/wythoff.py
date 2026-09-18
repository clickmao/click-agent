def solve(text: str) -> str:
    a, b = map(int, text.split())
    cap = max(a, b) + 1
    losing = set()
    seen = set()
    for n in range(cap + 1):
        x = int(n * (1 + 5 ** 0.5) / 2)
        y = x + n
        if x > cap or y > cap:
            break
        losing.add((x, y))

    def is_losing(p, q):
        return (min(p, q), max(p, q)) in losing

    if is_losing(a, b):
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if is_losing(a - i, b - j):
                if best is None or (i, j) < best:
                    best = (i, j)
    return "WIN %d %d" % best
