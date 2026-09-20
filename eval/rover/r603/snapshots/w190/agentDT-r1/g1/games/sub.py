def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = sorted(int(x) for x in tokens[2:2 + k])

    winning = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in steps:
            if s > m:
                break
            if not winning[m - s]:
                winning[m] = True
                break

    if not winning[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not winning[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
