"""取石子游戏: 取走最后一颗者胜, 输出先手胜负与最小必胜首取数。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    steps = sorted(map(int, lines[1].split()))

    win = [False] * (n + 1)
    for m in range(1, n + 1):
        for s in steps:
            if s <= m and not win[m - s]:
                win[m] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
