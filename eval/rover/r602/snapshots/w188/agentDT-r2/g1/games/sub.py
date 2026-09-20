def solve(text):
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split()))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for mv in moves:
            if mv <= i and not win[i - mv]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for mv in moves:
        if mv <= n and not win[n - mv]:
            return 'WIN ' + str(mv)
    return 'LOSE'
