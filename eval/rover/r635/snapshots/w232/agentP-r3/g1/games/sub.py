def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n')]
    while lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return 'LOSE'
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split()))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if win[n]:
        for s in moves:
            if s <= n and not win[n - s]:
                return 'WIN ' + str(s)
    return 'LOSE'
