def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    s = sorted(int(x) for x in lines[1].split())
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for take in s:
            if take > x:
                break
            if not win[x - take]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    for take in s:
        if n - take >= 0 and not win[n - take]:
            return 'WIN ' + str(take)
    return 'LOSE'
