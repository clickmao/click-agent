def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = sorted(int(x) for x in tokens[2:2 + k])

    losing = [False] * (n + 1)
    for total in range(1, n + 1):
        win = False
        for s in steps:
            if s <= total and losing[total - s]:
                win = True
                break
        losing[total] = not win

    for s in steps:
        if s <= n and losing[n - s]:
            return "WIN " + str(s)
    return "LOSE"
