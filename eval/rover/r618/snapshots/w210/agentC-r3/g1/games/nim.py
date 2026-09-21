def solve(text):
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    a = list(map(int, lines[1].split()))
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
