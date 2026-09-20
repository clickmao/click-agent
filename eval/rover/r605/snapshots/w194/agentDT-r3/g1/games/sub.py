"""Game: subtraction game, win/lose and smallest winning move."""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())
    dp = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not dp[i - s]:
                dp[i] = True
                break
    if not dp[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not dp[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
