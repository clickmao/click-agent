def solve(text):
    toks = text.split()
    if not toks:
        return ''
    m = int(toks[0])
    a = [int(x) for x in toks[1:1 + m]]
    x = 0
    for v in a:
        x ^= v
    if x == 0:
        return 'LOSE'
    for idx, v in enumerate(a, 1):
        r = v ^ x
        if r < v:
            return 'WIN %d %d' % (idx, v - r)
    return 'LOSE'
