def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    moves = []
    while idx < len(lines) and len(moves) < k:
        for tok in lines[idx].split():
            moves.append(int(tok))
        idx += 1
    moves = moves[:k]
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        w = False
        for s in moves:
            if s <= x and not win[x - s]:
                w = True
                break
        win[x] = w
    if not win[n]:
        return 'LOSE'
    best = None
    for s in moves:
        if s <= n and not win[n - s]:
            if best is None or s < best:
                best = s
    return 'WIN %d' % best
