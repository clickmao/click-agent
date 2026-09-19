def solve(text: str) -> str:
    data = text.split()
    m = int(data[0])
    a = [int(x) for x in data[1:1 + m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        t = a[idx] ^ x
        if t < a[idx]:
            return 'WIN %d %d' % (idx + 1, a[idx] - t)
    return 'LOSE'
