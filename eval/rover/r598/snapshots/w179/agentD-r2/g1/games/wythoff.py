def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])
    seen = set()
    pairs = []
    for n in range(0, 40):
        x = (n * (1 + 5 ** 0.5)) / 2.0
        c = int(x + 1e-9)
        d = c + n
        if c > 30 and d > 30:
            break
        pairs.append((c, d))
    def losing(p, q):
        if p > q:
            p, q = q, p
        for c, d in pairs:
            if c == p and d == q:
                return True
        return False
    if losing(a, b):
        return "LOSE"
    best = None
    # remove from pile 1 only
    for i in range(1, a + 1):
        if losing(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    # remove from pile 2 only
    for j in range(1, b + 1):
        if losing(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # remove same amount from both
    for t in range(1, min(a, b) + 1):
        if losing(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand
    return "WIN %d %d" % best
