def _is_losing(p: int, q: int) -> bool:
    if p > q:
        p, q = q, p
    n = 0
    while True:
        ai = int((n * (1 + 5 ** 0.5)) / 2 + 1e-9)
        bi = ai + n
        if ai > p or bi > q:
            return False
        if ai == p and bi == q:
            return True
        n += 1


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _is_losing(a - i, b - j):
                best = (i, j)
                break
        else:
            continue
        break
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
