def solve(text):
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    s = sorted(map(int, lines[1].split()))
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        ok = False
        for x in s:
            if x <= m and not win[m - x]:
                ok = True
                break
        win[m] = ok
    if not win[n]:
        return 'LOSE'
    for x in s:
        if x <= n and not win[n - x]:
            return 'WIN %d' % x
    return 'LOSE'
