# Subtraction game: report the winning first move or LOSE.

def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = [int(x) for x in tokens[2:2 + k]]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN ' + str(best)
