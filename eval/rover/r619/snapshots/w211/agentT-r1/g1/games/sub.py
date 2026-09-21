"""取石子子游戏。"""


def solve(text: str) -> str:
    toks = text.split()
    p = 0
    n = int(toks[p]); p += 1
    k = int(toks[p]); p += 1
    moves = sorted(int(toks[p + i]) for i in range(k))

    win = [False] * (n + 1)
    for t in range(1, n + 1):
        for m in moves:
            if m <= t and not win[t - m]:
                win[t] = True
                break

    if not win[n]:
        return 'LOSE'
    for m in moves:
        if m <= n and not win[n - m]:
            return 'WIN %d' % m
    return 'LOSE'
