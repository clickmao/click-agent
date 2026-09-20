"""取石子子游戏: 先手必胜/必败判定, 以及数值最小的必胜首取数。"""


def solve(text):
    lines = text.split('\n')
    n, k = map(int, lines[0].split()[:2])
    steps = sorted(set(int(x) for x in lines[1].split()[:k]))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(i - s >= 0 and not win[i - s] for s in steps)
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if n - s >= 0 and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
