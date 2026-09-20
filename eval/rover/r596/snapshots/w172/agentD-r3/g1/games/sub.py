"""Subtraction game: WIN m (smallest winning first move) or LOSE."""


def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    parts = lines[idx].split()
    n = int(parts[0])
    k = int(parts[1])
    idx += 1
    moves = []
    while idx < len(lines) and len(moves) < k:
        moves.extend(int(x) for x in lines[idx].split())
        idx += 1
    moves = sorted(moves)
    # dp[i] = True 表示剩余 i 颗石子时、轮到当前行动者有必胜策略
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
    first = None
    for s in moves:
        if s <= n and not dp[n - s]:
            first = s
            break
    return 'WIN %d' % first
