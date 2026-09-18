def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = [int(x) for x in tokens[2:2 + k]]
    steps.sort()
    win = [False] * (n + 1)
    best = [0] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                best[i] = s
                break
    if not win[n]:
        return "LOSE"
    return "WIN %d" % best[n]
