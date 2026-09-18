"""取石子子游戏: 必胜/必败判定 + 最小必胜首取数。

读入: 第一行 n k; 第二行 k 个互不相同的步数(含 1)。
输出: 'WIN m' 或 'LOSE'。
"""


def _win_table(n, steps):
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        w = False
        for s in steps:
            if s > x:
                continue
            if not win[x - s]:
                w = True
                break
        win[x] = w
    return win


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    steps = list(map(int, lines[1].split()))[:k]
    win = _win_table(n, steps)
    if not win[n]:
        return 'LOSE'
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
