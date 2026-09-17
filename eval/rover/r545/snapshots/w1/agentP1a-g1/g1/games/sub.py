
def solve(text: str) -> str:
    data = text.split()
    n = int(data[0])
    k = int(data[1])
    moves = sorted(int(x) for x in data[2:2 + k])
    win = [False] * (n + 1)
    for total in range(1, n + 1):
        for mv in moves:
            if mv > total:
                break
            if not win[total - mv]:
                win[total] = True
                break
    if not win[n]:
        return 'LOSE'
    for mv in moves:
        if mv <= n and not win[n - mv]:
            return 'WIN %d' % mv
    return 'LOSE'
