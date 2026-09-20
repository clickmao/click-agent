def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n')]
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    moves = []
    while len(moves) < k and idx < len(lines):
        moves.extend(int(x) for x in lines[idx].split())
        idx += 1
    moves = sorted(set(m for m in moves if 1 <= m <= n))

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for m in moves:
            if m > i:
                break
            if not win[i - m]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for m in moves:
        if m <= n and not win[n - m]:
            return 'WIN %d' % m
    return 'LOSE'
