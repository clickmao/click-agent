def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    heaps = [int(x) for x in data[1:1 + m]]
    x = 0
    for h in heaps:
        x ^= h
    if x == 0:
        return 'LOSE'
    for i in range(m):
        t = heaps[i] ^ x
        if t < heaps[i]:
            return 'WIN ' + str(i + 1) + ' ' + str(heaps[i] - t)
    return 'LOSE'
