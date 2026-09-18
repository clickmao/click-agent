def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    s = list(map(int, lines[idx].split()))[:k]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for move in s:
            if move <= i and not win[i - move]:
                win[i] = True
                break
    if win[n]:
        best = None
        for move in sorted(s):
            if move <= n and not win[n - move]:
                best = move
                break
        return 'WIN %d' % best
    return 'LOSE'
