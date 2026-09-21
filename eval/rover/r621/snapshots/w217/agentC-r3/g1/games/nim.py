def solve(text: str) -> str:
    tok = []
    for ln in text.split('\n'):
        tok.extend(ln.split())
    it = iter(tok)
    m = int(next(it))
    piles = [int(next(it)) for _ in range(m)]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i, p in enumerate(piles):
        t = p ^ x
        if t < p:
            return 'WIN %d %d' % (i + 1, p - t)
    return 'LOSE'
