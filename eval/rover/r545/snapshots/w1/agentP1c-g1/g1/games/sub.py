def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    moves = sorted(set(map(int, lines[1].split()))[:k])
    win = [False] * (n + 1)
    best = [None] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                best[i] = s
                break
    if win[n]:
        return 'WIN %d' % best[n]
    return 'LOSE'
