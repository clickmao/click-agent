def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    steps = sorted(int(x) for x in lines[2:2 + k])
    # win[pos] = True iff player to move wins with pos stones left
    win = [False] * (n + 1)
    for pos in range(1, n + 1):
        for s in steps:
            if s <= pos and not win[pos - s]:
                win[pos] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN {0}'.format(s)
    return 'LOSE'
