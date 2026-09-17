def solve(text):
    data = list(map(int, text.split()))
    m = data[0]
    a = data[1:1 + m]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i, v in enumerate(a):
        t = x ^ v
        if t < v:
            return 'WIN ' + str(i + 1) + ' ' + str(v - t)
    return 'LOSE'
