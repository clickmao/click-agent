def solve(text):
    toks = text.split()
    if len(toks) < 2:
        return ''
    n = int(toks[0])
    k = int(toks[1])
    s = sorted(int(x) for x in toks[2:2 + k])
    win = [False] * (n + 1)
    for t in range(1, n + 1):
        for a in s:
            if a <= t and not win[t - a]:
                win[t] = True
                break
    if not win[n]:
        return 'LOSE'
    for a in s:
        if a <= n and not win[n - a]:
            return 'WIN %d' % a
    return 'LOSE'
