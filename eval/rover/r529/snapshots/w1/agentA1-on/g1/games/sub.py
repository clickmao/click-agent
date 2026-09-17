"""取石子子游戏 (Subtraction Game) 的胜负判定与最小必胜首取。

规格:
  第一行: n k  (1<=n<=80 石子数, 1<=k<=12 可选步数个数)
  第二行: k 个互不相同的整数 s1..sk (1<=si<=12, 保证含 1)
玩法: 两人轮流取, 每次取走恰好某个允许数目, 取走最后一颗者胜。
输出: 先手必胜 -> "WIN m" (m 为数值最小的必胜首取数); 先手必败 -> "LOSE"。

判定: dp[x] = 局面剩 x 颗时先手是否必胜。dp[0]=False (无石子可取即败)。
dp[x] = 存在 s<=x 使 dp[x-s] 为 False。
"""
import math


def solve(text: str) -> str:
    """纯函数: stdin 文本 -> stdout 文本 (不带末尾换行)。"""
    lines = text.split('\n')
    n, k = (int(x) for x in lines[0].split())
    steps = [int(x) for x in lines[1].split()][:k]
    win = [False] * (n + 1)
    # dp[0] = False (无路可走者败)
    for x in range(1, n + 1):
        win[x] = any(s <= x and not win[x - s] for s in steps)
    if not win[n]:
        return 'LOSE'
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    # 逻辑上不可达 (win[n] 为真时必有致败着法)
    return 'LOSE'
