def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    moves = list(map(int, lines[1].split()))
    # win[i] = True 表示有 i 颗石子时轮到行动的一方有必胜策略
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
            if best is None or s < best:
                best = s
    return 'WIN ' + str(best)
