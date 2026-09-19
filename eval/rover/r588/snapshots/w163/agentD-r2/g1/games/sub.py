def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    s = sorted(int(x) for x in lines[2:])
    win = [False] * (n + 1)
    best = [None] * (n + 1)
    for i in range(1, n + 1):
        for m in s:
            if m <= i and not win[i - m]:
                win[i] = True
                best[i] = m
                break
    if win[n]:
        return 'WIN %d' % best[n]
    return 'LOSE'
