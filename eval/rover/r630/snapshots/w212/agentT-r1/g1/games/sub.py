"""取石子子游戏（subtraction game）必胜/必败判定。

输入格式：第一行 ``n k``（1<=n<=80 石子数，1<=k<=12 可选步数个数），第二行 k 个
互不相同的整数（1<=si<=12，且保证含 1）。
玩法：两人轮流取，每次取走恰好某个允许的数目，取走最后一颗者胜。
输出：先手必胜输出 ``WIN m``（m 为数值最小的必胜首取数）；必败输出 ``LOSE``。
"""


def solve(text):
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split()))
    # win[i] = 还剩 i 颗石子时轮到走子的一方可否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
