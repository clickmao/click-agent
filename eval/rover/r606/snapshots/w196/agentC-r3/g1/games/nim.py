def solve(text):
    parts = text.split()
    m = int(parts[0])
    piles = [int(x) for x in parts[1:1 + m]]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN ' + str(idx + 1) + ' ' + str(piles[idx] - target)
    return 'LOSE'
