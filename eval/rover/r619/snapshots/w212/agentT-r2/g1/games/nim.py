def solve(text):
    lines = text.split()
    m = int(lines[0])
    a = [int(x) for x in lines[1:1 + m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = a[i] ^ x
        if target < a[i]:
            return 'WIN ' + str(i + 1) + ' ' + str(a[i] - target)
    return 'LOSE'
