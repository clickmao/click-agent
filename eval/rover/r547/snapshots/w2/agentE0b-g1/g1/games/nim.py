def solve(text):
    lines = [l for l in text.splitlines() if l.strip() != '']
    m = int(lines[0])
    a = list(map(int, lines[1].split()))[:m]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i, v in enumerate(a):
        t = v ^ x
        if t < v:
            return 'WIN ' + str(i + 1) + ' ' + str(v - t)
    return 'LOSE'
