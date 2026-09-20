def solve(text):
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].strip())
    idx += 1
    piles = list(map(int, lines[idx].split()))
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i in range(len(piles)):
        target = piles[i] ^ x
        if target < piles[i]:
            return 'WIN ' + str(i + 1) + ' ' + str(piles[i] - target)
    return 'LOSE'
