"""取石子子游戏: 返回 "WIN m"（m 为数值最小必胜首取数）或 "LOSE"。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1].strip() == '':
        lines.pop()
    n, k = (int(x) for x in lines[0].split())
    steps = sorted(int(x) for x in lines[1].split())

    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s > x:
                break
            if not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
