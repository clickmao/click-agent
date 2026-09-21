def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    steps = [int(x) for x in lines[2:2 + k]]
    steps.sort()

    # dp[i] = True 表示剩 i 颗时当前行动者必胜
    dp = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if not dp[i - s]:
                dp[i] = True
                break

    if not dp[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not dp[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
