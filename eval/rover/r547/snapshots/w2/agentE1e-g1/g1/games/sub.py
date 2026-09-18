def solve(text: str) -> str:
    lines = text.splitlines()
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
    moves = sorted(moves[:k])
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
