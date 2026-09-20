def solve(text):
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    s = list(map(int, lines[1].split()))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for step in s:
            if step <= i and not win[i - step]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for step in s:
        if step <= n and not win[n - step]:
            if best is None or step < best:
                best = step
    return 'WIN ' + str(best)
