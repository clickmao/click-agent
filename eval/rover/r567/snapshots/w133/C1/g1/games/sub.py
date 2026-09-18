def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    steps = list(map(int, lines[idx].split()))

    win = [False] * (n + 1)
    for total in range(1, n + 1):
        for s in steps:
            if s <= total and not win[total - s]:
                win[total] = True
                break

    if not win[n]:
        return "LOSE"

    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
