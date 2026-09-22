def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    moves = sorted(set(map(int, lines[idx].split())))
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        w = False
        for s in moves:
            if s > x:
                break
            if not win[x - s]:
                w = True
                break
        win[x] = w
    if not win[n]:
        return "LOSE"
    best = None
    for s in moves:
        if s <= n and not win[n - s]:
            best = s
            break
    return "WIN %d" % best
