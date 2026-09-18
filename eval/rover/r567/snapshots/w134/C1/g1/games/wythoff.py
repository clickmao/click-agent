def _losing(x, y):
    a, b = min(x, y), max(x, y)
    i = 0
    p, q = 0, 0
    while p < a or q < b:
        i += 1
        p = i * (1 + 5 ** 0.5) // 2
        q = p + i
    return p == a and q == b


def solve(text: str) -> str:
    a, b = map(int, text.split())
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _losing(a - i, b - j):
                best = (i, j)
                break
        if best:
            break
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
