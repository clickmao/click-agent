def solve(text):
    lines = text.split()
    data = list(map(int, lines))
    n, k = data[0], data[1]
    s = data[2:2 + k]
    win = [False] * (n + 1)
    for t in range(1, n + 1):
        for x in s:
            if x <= t and not win[t - x]:
                win[t] = True
                break
    if not win[n]:
        return 'LOSE'
    for x in sorted(s):
        if x <= n and not win[n - x]:
            return 'WIN ' + str(x)
    return 'LOSE'
