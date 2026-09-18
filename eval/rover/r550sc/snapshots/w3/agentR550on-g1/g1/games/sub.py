def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = (int(x) for x in lines[0].split())
    moves = [int(x) for x in lines[1].split()][:k]
    dp = [False] * (n + 1)
    for i in range(1, n + 1):
        win = False
        for s in moves:
            if s <= i and not dp[i - s]:
                win = True
                break
        dp[i] = win
    if not dp[n]:
        return 'LOSE'
    for s in sorted(moves):
        if s <= n and not dp[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
