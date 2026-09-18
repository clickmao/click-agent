def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1].strip() == '':
        lines.pop()
    n, k = (int(x) for x in lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())[:k]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for s in moves:
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN %d' % best
