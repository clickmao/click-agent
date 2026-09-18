def solve(text):
    lines = text.splitlines()
    if not lines:
        return 'LOSE'
    head = lines[0].split()
    if not head:
        return 'LOSE'
    m = int(head[0])
    if len(lines) > 1:
        piles = [int(x) for x in lines[1].split()]
    else:
        piles = []
    piles = piles[:m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for i in range(len(piles)):
        target = piles[i] ^ x
        if target < piles[i]:
            take = piles[i] - target
            return 'WIN ' + str(i + 1) + ' ' + str(take)
    return 'LOSE'
