def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    steps = list(map(int, lines[idx].split()))[:k]
    steps = sorted(steps)

    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s <= x and not win[x - s]:
                win[x] = True
                break

    if win[n]:
        for s in steps:
            if s <= n and not win[n - s]:
                return 'WIN ' + str(s)
    return 'LOSE'
