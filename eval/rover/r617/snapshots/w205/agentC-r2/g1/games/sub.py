"""取石子游戏 (subtraction game) 必败/必胜判定。

读入: 第一行两个整数 n k (1<=n<=80, 1<=k<=12); 第二行 k 个互不相同的整数 si (1<=si<=12, 含 1)。
输出: 必胜输出 'WIN m' (m 为数值最小的必胜首取数); 必败输出 'LOSE'。末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, _k = int(lines[0].split()[0]), int(lines[0].split()[1])
    moves = [int(x) for x in lines[1].split()]
    moves = sorted(set(moves))

    # win[i]: 剩余 i 颗时轮到行动方是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        w = False
        for s in moves:
            if s <= i and not win[i - s]:
                w = True
                break
        win[i] = w

    if win[n]:
        for s in moves:
            if s <= n and not win[n - s]:
                return 'WIN ' + str(s)
        return 'LOSE'
    return 'LOSE'
