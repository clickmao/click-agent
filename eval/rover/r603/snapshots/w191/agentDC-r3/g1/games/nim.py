def solve(text):
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    a = list(map(int, lines[1].split()))[:m]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i, v in enumerate(a):
        target = v ^ x
        if target < v:
            return 'WIN ' + str(i + 1) + ' ' + str(v - target)
    return 'LOSE'
