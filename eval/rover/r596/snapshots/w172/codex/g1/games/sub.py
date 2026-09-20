def solve(text: str) -> str:
    tokens = text.split()
    n, k = int(tokens[0]), int(tokens[1])
    steps = [int(x) for x in tokens[2:2 + k]]
    steps.sort()

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
