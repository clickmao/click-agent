"""取石子游戏：先手必胜/必败判定。

入参 text 为完整 stdin 文本，返回应当写出的 stdout 文本（末尾不带换行）。
"""


def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    steps = sorted(int(x) for x in lines[2:2 + k])

    # 取走最后一颗者胜：n=0 为必败态。
    win = [False] * (n + 1)
    for t in range(1, n + 1):
        win[t] = any(s <= t and not win[t - s] for s in steps)

    if not win[n]:
        return 'LOSE'
    best = min(s for s in steps if s <= n and not win[n - s])
    return 'WIN %d' % best
