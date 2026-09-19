"""取石子子游戏必败/必胜判定。"""


def solve(text):
    tok = text.split()
    n, k = int(tok[0]), int(tok[1])
    S = sorted(int(tok[2 + i]) for i in range(k))
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in S:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in S:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
