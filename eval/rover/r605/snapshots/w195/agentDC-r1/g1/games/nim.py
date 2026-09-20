def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    a = [int(x) for x in lines[1].split()]
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
