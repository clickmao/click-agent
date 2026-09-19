def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = (int(x) for x in lines[0].split())
    steps = sorted(int(x) for x in lines[1].split()[:k])

    win = [False] * (n + 1)
    for cur in range(1, n + 1):
        for s in steps:
            if s > cur:
                break
            if not win[cur - s]:
                win[cur] = True
                break

    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
