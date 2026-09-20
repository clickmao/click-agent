"""Subtraction game: first player win/lose and smallest winning first move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split()))
    moves = [s for s in moves if 1 <= s <= n]
    if not moves:
        return 'LOSE'
    # dp[x] = True if the player to move with x stones wins
    dp = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s > x:
                break
            if not dp[x - s]:
                dp[x] = True
                break
    if not dp[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not dp[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
