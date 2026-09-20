def _win(n, steps):
    dp = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s <= x and not dp[x - s]:
                dp[x] = True
                break
    return dp


def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    steps = sorted(int(v) for v in lines[2:2 + k])
    dp = _win(n, steps)
    if not dp[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not dp[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
