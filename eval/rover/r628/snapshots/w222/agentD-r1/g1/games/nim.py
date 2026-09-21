def solve(text):
    lines = text.split()
    m = int(lines[0])
    a = [int(x) for x in lines[1:1 + m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        t = a[idx] ^ x
        if t < a[idx]:
            return 'WIN ' + str(idx + 1) + ' ' + str(a[idx] - t)
    return 'LOSE'
