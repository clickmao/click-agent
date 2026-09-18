"""取石子子游戏：必胜/必败判定，WIN 给数值最小的必胜首取数。"""


def solve(text: str) -> str:
    toks = text.split()
    n = int(toks[0])
    k = int(toks[1])
    steps = [int(t) for t in toks[2:2 + k]]
    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in steps:
            if s <= m and not win[m - s]:
                win[m] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in sorted(set(steps)):
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
