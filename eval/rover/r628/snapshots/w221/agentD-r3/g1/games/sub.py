def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    n = int(first[0])
    k = int(first[1])
    moves = [int(x) for x in lines[1].split()[:k]]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN ' + str(best)
