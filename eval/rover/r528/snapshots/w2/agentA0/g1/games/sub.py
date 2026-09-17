"""取石子子游戏 (subtraction game) 胜负判定。

输入文本 (stdin 全部):
    第一行: n k   (1<=n<=80 石子数, 1<=k<=12 可选步数个数)
    第二行: k 个互不相同整数 s1..sk (1<=si<=12, 保证含 1)

玩法: 两人轮流取, 每次取走恰好某个允许数目, 取走最后一颗者胜。
输出: 先手必胜 -> 一行 `WIN m` (m 为数值最小的必胜首取数); 否则一行 `LOSE`。
末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = (int(x) for x in lines[0].split())
    steps = sorted(int(x) for x in lines[1].split()[:k])

    # win[i] = 剩余 i 颗且轮到自己时, 是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'

    # 数值最小的必胜首取数: 取 s 后留下 i-s 为必败态
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN {}'.format(s)
    return 'LOSE'  # 不可达 (win[n] 为真时必存在该 s)
