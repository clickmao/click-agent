"""Wythoff 博弈必败点判定。

输入格式:
    一行两个整数 a b (1<=a<=25, 1<=b<=25)

玩法: 每次可选 (i) 从任意一堆中取走任意正数目的石子, 或
      (ii) 从两堆中同时取走相同的正数目的石子; 取走最后一颗石子者胜。

输出: 先手必败时输出一行 `LOSE`;
      否则输出一行 `WIN i j` —— 从第一堆取 i 颗、从第二堆取 j 颗,
      且 (i, j) 在全部必胜着法中按字典序最小 (先比 i 再比 j; i, j >= 0 且不同时为 0)。
"""


def solve(text: str) -> str:
    """返回 WIN i j 或 LOSE, 末尾不带换行。"""
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    # 直接对 26x26 棋盘做局面 DP:
    # losing[x][y] 表示轮到行动方在两堆分别为 (x, y) 时必败。
    # 允许的着法: 从第一堆取任意正数、从第二堆取任意正数、或两堆同取相同正数。
    # 由小到大递推 (x+y 单调递减, 因此按 x+y 升序即可覆盖所有后继)。
    losing = [[False] * 26 for _ in range(26)]
    for total in range(0, 51):
        for x in range(0, 26):
            y = total - x
            if y < 0 or y > 25:
                continue
            if x > 25 or y > 25:
                continue
            win = False
            # (i) 从第一堆取任意正数
            for t in range(1, x + 1):
                if losing[x - t][y]:
                    win = True
                    break
            if not win:
                # (i) 从第二堆取任意正数
                for t in range(1, y + 1):
                    if losing[x][y - t]:
                        win = True
                        break
            if not win:
                # (ii) 两堆同时取相同正数
                for t in range(1, min(x, y) + 1):
                    if losing[x - t][y - t]:
                        win = True
                        break
            losing[x][y] = not win

    if losing[a][b]:
        return 'LOSE'

    # 枚举所有合法着法, 取字典序最小 (先比 i 再比 j)
    best = None
    # (i) 从第一堆取 i 颗, j = 0
    for i in range(1, a + 1):
        if losing[a - i][b]:
            if best is None or (i, 0) < best:
                best = (i, 0)
    # (i) 从第二堆取 j 颗, i = 0
    for j in range(1, b + 1):
        if losing[a][b - j]:
            if best is None or (0, j) < best:
                best = (0, j)
    # (ii) 两堆同时取相同数目 t 颗
    for t in range(1, min(a, b) + 1):
        if losing[a - t][b - t]:
            if best is None or (t, t) < best:
                best = (t, t)

    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
