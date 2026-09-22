"""取石子子游戏：减法游戏必胜/必败判定。

输入格式：第一行 n k（石子数、可选步数个数）；
第二行 k 个互不相同的整数，表示一步可取走的石子数（保证含 1）。
取走最后一颗者胜。
输出：先手必胜输出 'WIN m'（m 为数值最小的必胜首取数）；否则输出 'LOSE'。
"""


def solve(text):
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    moves = sorted(int(x) for x in lines[1].split())
    # win[x] = True 表示剩余 x 颗时轮到当前行动者有必胜策略
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        res = False
        for s in moves:
            if s <= x and not win[x - s]:
                res = True
                break
        win[x] = res
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    # 正常情况下不可达
    return 'LOSE'
