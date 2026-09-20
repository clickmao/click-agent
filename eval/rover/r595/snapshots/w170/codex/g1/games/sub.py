def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = [int(tokens[2 + i]) for i in range(k)]
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN %d' % best
