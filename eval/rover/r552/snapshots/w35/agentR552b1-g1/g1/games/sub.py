def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    s = sorted(map(int, lines[1].split()))
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for t in s:
            if t > x:
                break
            if not win[x - t]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    for t in s:
        if t <= n and not win[n - t]:
            return 'WIN ' + str(t)
    return 'LOSE'
