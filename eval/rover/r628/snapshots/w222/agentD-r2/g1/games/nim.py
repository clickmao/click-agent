def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    a = [int(x) for x in lines[1].split()[:m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for i, v in enumerate(a):
        t = v ^ x
        if t < v:
            return 'WIN %d %d' % (i + 1, v - t)
    return 'LOSE'
