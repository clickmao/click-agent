def solve(text: str) -> str:
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    n, k = map(int, lines[0].split())
    steps = sorted(int(x) for x in lines[1].split())
    win = [False] * (n + 1)
    for rem in range(1, n + 1):
        for s in steps:
            if s <= rem and not win[rem - s]:
                win[rem] = True
                break
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
