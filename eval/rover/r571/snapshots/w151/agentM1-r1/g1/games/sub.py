def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    moves = list(map(int, lines[idx].split()))[:k]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if win[n]:
        best = None
        for s in moves:
            if s <= n and not win[n - s]:
                if best is None or s < best:
                    best = s
        return 'WIN %d' % best
    return 'LOSE'
