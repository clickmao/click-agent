"""取石子子游戏必败/必胜判定。

输入格式:
    第一行两个整数 n k (1<=n<=80 为石子数, 1<=k<=12 为可选步数个数)
    第二行 k 个互不相同的整数 s1..sk (1<=si<=12, 且保证其中含 1)

玩法: 两人轮流取, 每次取走恰好某个允许的数目, 取走最后一颗者胜。

输出: 先手有必胜策略时输出一行 `WIN m` (m 为数值最小的必胜首取数);
      先手必败时输出一行 `LOSE`。
"""


def solve(text: str) -> str:
    """返回 WIN m 或 LOSE, 末尾不带换行。"""
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    steps = sorted(int(x) for x in lines[2:2 + k])

    # win[i] = 石子数为 i 时当前行动者有必胜策略
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
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
