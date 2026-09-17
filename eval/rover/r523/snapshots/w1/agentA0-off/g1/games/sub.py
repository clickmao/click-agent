"""sub: 取石子子游戏必败/必胜判定 (减法游戏)。

输入:
    第一行两个整数 n k (1<=n<=80 为石子数, 1<=k<=12 为可选步数个数)
    第二行 k 个互不相同的整数 s1..sk (1<=si<=12, 且保证其中含 1)

玩法:
    两人轮流取, 每次取走恰好某个允许的数目, 取走最后一颗者胜。

输出:
    先手有必胜策略时输出一行 `WIN m` (m 为数值最小的必胜首取数);
    先手必败时输出一行 `LOSE`。
"""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    moves = sorted(int(tokens[2 + i]) for i in range(k))

    # win[x] = True 表示面对 x 颗石子者必胜
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s > x:
                break
            if not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
