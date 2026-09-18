def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    moves = list(map(int, lines[1].split()))[:k]

    # win[x] = True iff player to move with x stones has a winning strategy
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s <= x and not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return "LOSE"
    best = None
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            best = s
            break
    return "WIN %d" % best
