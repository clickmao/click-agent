def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    while lines[idx].strip() == '':
        idx += 1
    moves = list(map(int, lines[idx].split()))
    win = [False] * (n + 1)
    for t in range(1, n + 1):
        for s in moves:
            if s <= t and not win[t - s]:
                win[t] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
