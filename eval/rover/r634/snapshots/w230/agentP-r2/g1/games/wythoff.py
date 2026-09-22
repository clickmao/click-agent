def solve(text: str) -> str:
    parts = text.split()
    a = int(parts[0])
    b = int(parts[1])
    a, b = min(a, b), max(a, b)
    limit = 60
    losing = []
    used = set()
    n = 0
    while n <= limit / 2 + 2:
        x = int(n * (1 + 5 ** 0.5) / 2)
        y = x + n
        if x > limit and y > limit:
            break
        if x not in used and y not in used:
            losing.append((x, y))
            used.add(x)
            used.add(y)
        n += 1

    def is_lose(p, q):
        p, q = min(p, q), max(p, q)
        if p == q:
            return False
        for (x, y) in losing:
            if x == p and y == q:
                return True
        return False

    if is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(0, a // 1 + 1):
        j = i
        if j > b:
            break
        if is_lose(a - i, b - j):
            if best is None or (i, j) < best:
                best = (i, j)
    if a == b:
        pass
    for j in range(0, b + 1):
        i = 0
        if is_lose(a - i, b - j):
            if best is None or (i, j) < best:
                best = (i, j)
    for i in range(0, a + 1):
        j = 0
        if is_lose(a - i, b - j):
            if best is None or (i, j) < best:
                best = (i, j)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
