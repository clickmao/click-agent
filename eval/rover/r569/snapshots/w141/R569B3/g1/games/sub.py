def solve(text):
    lines = text.splitlines()
    if not lines:
        return ""
    first = lines[0].split()
    if len(first) < 2:
        return ""
    n = int(first[0])
    k = int(first[1])
    steps = []
    if len(lines) > 1:
        steps = [int(x) for x in lines[1].split()][:k]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        ok = False
        for s in steps:
            if s <= i and not win[i - s]:
                ok = True
                break
        win[i] = ok
    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
