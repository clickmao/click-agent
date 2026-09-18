def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    piles = [int(x) for x in tokens[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for p in range(m):
        r = piles[p] - (x ^ piles[p])
        if 0 < r <= piles[p]:
            return 'WIN %d %d' % (p + 1, r)
