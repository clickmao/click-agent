def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    first = lines[idx].split()
    n = int(first[0])
    k = int(first[1])
    idx += 1
    moves = []
    while len(moves) < k:
        for tok in lines[idx].split():
            moves.append(int(tok))
        idx += 1
    moves = sorted(moves)
    win = [False] * (n + 1)
    win[0] = False
    for i in range(1, n + 1):
        ok = False
        for s in moves:
            if s <= i and not win[i - s]:
                ok = True
                break
        win[i] = ok
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
