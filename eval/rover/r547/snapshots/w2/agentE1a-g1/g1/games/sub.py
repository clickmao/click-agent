def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    s = sorted(map(int, lines[1].split()))
    if n < s[0]:
        return 'LOSE'
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for take in s:
            if take <= i and not win[i - take]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for take in s:
        if take <= n and not win[n - take]:
            return 'WIN ' + str(take)
    return 'LOSE'
