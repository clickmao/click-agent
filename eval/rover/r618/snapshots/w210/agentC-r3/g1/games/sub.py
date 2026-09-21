def solve(text):
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    s = sorted(map(int, lines[1].split()))
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
            return 'WIN ' + str(x)
    return 'LOSE'
