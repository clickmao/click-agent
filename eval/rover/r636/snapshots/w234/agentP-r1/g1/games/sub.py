def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    s = sorted(int(x) for x in lines[1].split()[:k])
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for v in s:
            if v > i:
                break
            if not win[i - v]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for v in s:
        if v <= n and not win[n - v]:
            return 'WIN %d' % v
    return 'LOSE'
