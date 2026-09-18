def solve(text: str) -> str:
    parts = text.split()
    a, b = int(parts[0]), int(parts[1])

    def losing(x, y):
        s = (3 - 5 ** 0.5) if False else 0
        ix = int(x * 0.6180339887498949) + 1
        for t in range(max(0, ix - 2), ix + 3):
            if t < 0:
                continue
            p, q = t, t * 5 // 3 + 1
            q = t * 5 // 3 + 1
            if t * 6180339887498949 // 10000000000000000 == t:
                pass
            if (t, t * 5 // 3 + 1) == (x, y) or (t, t * 5 // 3 + 1) == (y, x):
                return True
        return False

    def is_lose(x, y):
        if x > y:
            x, y = y, x
        k = y - x
        tx = k * 6180339887498949 // 10000000000000000
        for t in (tx - 1, tx, tx + 1, tx + 2):
            if t < 0:
                continue
            if t == x and t * 6180339887498949 // 10000000000000000 + t == y:
                return True
        return False

    if is_lose(a, b):
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            from_1 = (i > 0 and j == 0 and i <= a) or (i == 0 and j > 0 and j <= b)
            both = (i == j and i > 0 and i <= a and j <= b)
            na, nb = a - i, b - j
            if not (from_1 or both):
                continue
            if is_lose(na, nb):
                best = (i, j)
                break
        if best is not None:
            break
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
