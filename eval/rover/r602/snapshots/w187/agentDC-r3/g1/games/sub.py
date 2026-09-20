def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    n, k = int(first[0]), int(first[1])
    moves = [int(x) for x in lines[1].split()]
    for i in range(1, k + 1):
        moves[i - 1] = moves[i - 1]
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
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN ' + str(best)
