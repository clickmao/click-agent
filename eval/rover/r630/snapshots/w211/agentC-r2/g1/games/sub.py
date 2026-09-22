"""取石子子游戏: 先手必胜/必败判定与最小必胜首取数。

输入文本格式:
    第一行: n k  (1<=n<=80 石子数, 1<=k<=12 可选步数个数)
    第二行: k 个互不相同整数 s1..sk (1<=si<=12, 保证含 1)

规则: 每次取走恰好某个允许的数目, 取走最后一颗者胜。
输出: 必胜 -> 'WIN m' (m 为数值最小的必胜首取数); 必败 -> 'LOSE'。
"""


def solve(text):
    lines = text.splitlines()
    first = lines[0].split()
    n = int(first[0])
    k = int(first[1])
    moves = [int(x) for x in lines[1].split()[:k]]
    # win[i] = 剩 i 颗时轮到行动的一方是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        w = False
        for m in moves:
            if m <= i and not win[i - m]:
                w = True
                break
        win[i] = w
    if not win[n]:
        return 'LOSE'
    for m in sorted(moves):
        if m <= n and not win[n - m]:
            return 'WIN ' + str(m)
    return 'LOSE'
