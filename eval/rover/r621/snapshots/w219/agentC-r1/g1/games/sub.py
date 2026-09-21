def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    n, k = map(int, lines[0].split())
    moves = sorted(set(int(x) for x in lines[1].split()))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if win[n]:
        for s in moves:
            if s <= n and not win[n - s]:
                return 'WIN %d' % s
        return 'LOSE'
    return 'LOSE'
