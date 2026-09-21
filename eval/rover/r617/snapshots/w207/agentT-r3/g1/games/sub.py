"""取石子子游戏：先手胜负判定，必胜时给出数值最小的首取数。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, _k = (int(x) for x in lines[0].split())
    steps = [int(x) for x in lines[1].split()]

    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in steps:
            if s <= m and not win[m - s]:
                win[m] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
