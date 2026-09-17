def _lose_pair(n):
    phi = (1 + 5 ** 0.5) / 2.0
    pairs = []
    used = set()
    r = 0
    while len(pairs) < n:
        a = r * phi
        ai = int(a)
        if ai == a:
            ai -= 1
        b = ai + r
        if ai not in used and b not in used:
            used.add(ai)
            used.add(b)
            pairs.append((ai, b))
        r += 1
    return pairs


def solve(text: str) -> str:
    a, b = map(int, text.split())
    if a > b:
        lo, hi = b, a
        swapped = True
    else:
        lo, hi = a, b
        swapped = False
    is_lose = False
    for p, q in _lose_pair(40):
        if lo == p and hi == q:
            is_lose = True
            break
        if p > lo:
            break
    if is_lose:
        return 'LOSE'
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            x, y = (na, nb) if na <= nb else (nb, na)
            lose = False
            for p, q in _lose_pair(40):
                if x == p and y == q:
                    lose = True
                    break
                if p > x:
                    break
            if not lose:
                best = (i, j)
                break
        if best is not None:
            break
    return 'WIN %d %d' % best
