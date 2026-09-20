"""取石子子游戏: 先手必胜/必败判定 + 数值最小的必胜首取数。

输入: 第一行两个整数 n k (1<=n<=80, 1<=k<=12); 第二行 k 个互不相同的整数 s1..sk (1<=si<=12, 含 1)。
每次取走恰好某个允许的数目, 取走最后一颗者胜。
输出: 先手必胜时 'WIN m' (m 为数值最小的必胜首取数); 否则 'LOSE'。
"""


def solve(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip() != '']
    idx = 0
    n, k = map(int, lines[idx].split())
    idx += 1
    moves = list(map(int, lines[idx].split()))
    idx += 1
    moves = moves[:k]

    # win[x] = 剩余 x 颗石子时, 当前行动方是否必胜
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s <= x and not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return 'LOSE'
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
