def solve(text):
    parts = text.split()
    m = int(parts[0])
    a = [int(x) for x in parts[1:1 + m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i in range(m):
        t = a[i] ^ x
        if t < a[i]:
            return 'WIN ' + str(i + 1) + ' ' + str(a[i] - t)
    return 'LOSE'
