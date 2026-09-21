def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = sorted(int(t) for t in tokens[2:2 + k])
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
