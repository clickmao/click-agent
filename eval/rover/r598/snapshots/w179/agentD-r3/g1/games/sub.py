def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    n, k = (int(x) for x in lines[idx].split())
    steps = None
    j = idx + 1
    while j < len(lines):
        parts = lines[j].split()
        if len(parts) >= k:
            try:
                steps = [int(x) for x in parts[:k]]
                break
            except ValueError:
                j += 1
                continue
        j += 1
    if steps is None:
        steps = []

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
