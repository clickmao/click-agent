"""取石子子游戏：先手必胜/必败判定。

读入: 第一行 n k; 第二行 k 个允许取数 (含 1)。
输出: 必胜时 "WIN m" (m 为数值最小的必胜首取数); 必败时 "LOSE"。
取走最后一颗者胜 -> 位置 n 是必败态 (面对 n 颗、无法再取而对方已取完, 实际 n=0 为必败)。
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(x) for x in lines[0].split())
    steps = sorted({int(x) for x in lines[1].split()})[:k]

    # dp[x] = 面对 x 颗石子时先手是否必胜
    dp = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s <= x and not dp[x - s]:
                dp[x] = True
                break

    if not dp[n]:
        return 'LOSE'
    # 数值最小的必胜首取数: 取 s 后留下必败态
    for s in steps:
        if s <= n and not dp[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
