def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    piles = [int(x) for x in data[1:1 + m]]

    xor = 0
    for a in piles:
        xor ^= a

    if xor == 0:
        return 'LOSE'

    for idx, a in enumerate(piles):
        target = a ^ xor
        if target < a:
            return 'WIN %d %d' % (idx + 1, a - target)
    return 'LOSE'
