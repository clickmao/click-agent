def solve(text):
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split())
    s = [int(x) for x in lines[1].split()]
    s = sorted(x for x in s if 1 <= x <= n)
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for x in s:
            if x <= i and not win[i - x]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for x in s:
        if x <= n and not win[n - x]:
            return 'WIN %d' % x
    return 'LOSE'
