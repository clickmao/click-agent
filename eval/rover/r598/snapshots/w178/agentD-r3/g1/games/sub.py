def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    steps = sorted(int(x) for x in lines[1].split()[:k])
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in steps:
            if s > m:
                break
            if not win[m - s]:
                win[m] = True
                break
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
