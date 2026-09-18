def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(t) for t in lines[0].split())
    steps = sorted(int(t) for t in lines[1].split()[:k])
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
