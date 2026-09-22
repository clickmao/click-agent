def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    n, k = (int(x) for x in lines[0].split())
    steps = [int(x) for x in lines[1].split()]
    steps = sorted(set(steps))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
