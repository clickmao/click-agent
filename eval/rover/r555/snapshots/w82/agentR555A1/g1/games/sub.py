def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    moves = sorted(map(int, lines[idx].split()))
    moves = [s for s in moves if 1 <= s <= n]
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
