"""取石子子游戏: 必胜/必败判定与最小必胜首取数。

约定: text 为该游戏的完整 stdin 文本; 返回应当写出的 stdout 文本, 末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return ''
    n, _k = (int(x) for x in lines[0].split())
    steps = sorted(int(x) for x in lines[1].split())
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in steps)
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
