def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    while lines[idx].strip() == "":
        idx += 1
    moves = sorted(int(t) for t in lines[idx].split()[:k])

    win = [False] * (n + 1)
    best = [0] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                best[i] = s
                break

    if not win[n]:
        return "LOSE"
    return "WIN " + str(best[n])
