def solve(text: str) -> str:
    data = text.split()
    idx = 0
    n = int(data[idx]); idx += 1
    k = int(data[idx]); idx += 1
    steps = sorted(int(data[idx + i]) for i in range(k))
    win = [False] * (n + 1)
    for total in range(1, n + 1):
        win[total] = any(s <= total and not win[total - s] for s in steps)
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
