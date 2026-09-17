def _parse(text):
    lines = text.split('\n')
    i = 0
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    m = int(lines[i].split()[0])
    i += 1
    while i < len(lines) and lines[i].strip() == '':
        i += 1
    piles = list(map(int, lines[i].split()))
    return m, piles


def solve(text):
    m, piles = _parse(text)
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(len(piles)):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN ' + str(idx + 1) + ' ' + str(piles[idx] - target)
    return 'LOSE'
