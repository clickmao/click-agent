"""取石子子游戏：先手必胜/必败判定。

输入格式：
第一行两个整数 n k (1<=n<=80, 1<=k<=12)
第二行 k 个互不相同的整数 s1..sk (1<=si<=12, 保证含 1)

输出：
先手必胜 -> 'WIN m'，m 为数值最小的必胜首取数
先手必败 -> 'LOSE'
solve 返回值末尾不带换行。
"""


def solve(text: str) -> str:
    lines = [ln for ln in text.split('\n') if ln.strip() != '']
    n, k = (int(x) for x in lines[0].split())
    moves = [int(x) for x in lines[1].split()]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
