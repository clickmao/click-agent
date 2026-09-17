def solve(text: str) -> str:
    tokens = text.split()
    m = int(tokens[0])
    heaps = [int(x) for x in tokens[1:1 + m]]

    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return 'LOSE'

    for idx in range(m):
        target = heaps[idx] ^ x
        if target < heaps[idx]:
            return 'WIN %d %d' % (idx + 1, heaps[idx] - target)
    return 'LOSE'
