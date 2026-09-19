def solve(text: str) -> str:
    lines = text.strip().split('\n')
    n, k = map(int, lines[0].split())
    moves = sorted(set(map(int, lines[1].split())))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for mv in moves:
            if mv <= i and not win[i - mv]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for mv in moves:
        if mv <= n and not win[n - mv]:
            best = mv
            break
    return 'WIN ' + str(best)
