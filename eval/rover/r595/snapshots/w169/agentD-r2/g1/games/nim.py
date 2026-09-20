def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    a = [int(x) for x in data[1:1 + m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for p in range(1, m + 1):
        target = a[p - 1] ^ x
        if target < a[p - 1]:
            r = a[p - 1] - target
            return 'WIN ' + str(p) + ' ' + str(r)
    return 'LOSE'
