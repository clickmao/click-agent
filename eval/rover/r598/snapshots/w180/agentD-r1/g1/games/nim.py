def solve(text: str) -> str:
    lines = text.split()
    m = int(lines[0])
    piles = [int(x) for x in lines[1:1 + m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for pi in range(m):
        target = piles[pi] ^ x
        if target < piles[pi]:
            r = piles[pi] - target
            return 'WIN {0} {1}'.format(pi + 1, r)
    return 'LOSE'
