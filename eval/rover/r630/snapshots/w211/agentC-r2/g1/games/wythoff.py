"""Wythoff 博弈: 判定先手胜负并给出字典序最小的必胜着法。

输入文本格式:
    一行两个整数 a b (1<=a<=25, 1<=b<=25)

规则: 每次可选 (i) 从任意一堆取走任意正数目的石子, 或 (ii) 从两堆
同时取走相同的正数目的石子; 取走最后一颗者胜。
输出: 必败 -> 'LOSE'; 否则 'WIN i j' (从第一堆取 i 颗、第二堆取 j 颗,
      (i,j) 在全部必胜着法中按字典序最小, i,j>=0 且不同时为 0)。
"""


def _losing(a, b):
    """dp 判定 (a,b) 是否为必败态: dp 值 True 表示轮到行动方必胜。"""
    dp = [[False] * (b + 1) for _ in range(a + 1)]
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                dp[i][j] = False
                continue
            w = False
            for k in range(1, i + 1):
                if not dp[i - k][j]:
                    w = True
                    break
            if not w:
                for k in range(1, j + 1):
                    if not dp[i][j - k]:
                        w = True
                        break
            if not w:
                t = min(i, j)
                for k in range(1, t + 1):
                    if not dp[i - k][j - k]:
                        w = True
                        break
            dp[i][j] = w
    return not dp[a][b]


def solve(text):
    parts = text.split()
    a = int(parts[0])
    b = int(parts[1])
    if _losing(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # 合法着法: 单堆取 (i==0 或 j==0) 或 两堆同取 (i==j)
            if not (i == 0 or j == 0 or i == j):
                continue
            if _losing(a - i, b - j):
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
