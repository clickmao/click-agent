"""wythoff: Wythoff 博弈必败点判定。

输入:
    一行两个整数 a b (1<=a<=25, 1<=b<=25)。

玩法:
    每次可选 (i) 从任意一堆中取走任意正数目的石子,
    或 (ii) 从两堆中同时取走相同正数目的石子; 取走最后一颗石子者胜。

输出:
    先手必败时输出 `LOSE`; 否则输出 `WIN i j`
    -- 从第一堆取 i 颗、第二堆取 j 颗, (i,j) 为全部必胜着法中字典序最小者
    (i,j >= 0 且不同时为 0)。
"""


def _losing(a: int, b: int) -> bool:
    """Wythoff 必败点判据: 设 x=min(a,b), y=max(a,b),
    必败当且仅当 x == floor((y-x) * phi), 其中 phi=(1+sqrt(5))/2。"""
    x, y = (a, b) if a <= b else (b, a)
    d = y - x
    # 用整数方式避免浮点误差: x == floor(d * 1.6180339887...) 判定
    # 等价形式: 存在 n 使 x = n*d 序号 -> 直接用精确连分数近似
    # 采用标准整数判据: x == (d * 1618033988749895) // 1000000000000000
    return x == (d * 1618033988749895) // 1000000000000000


def solve(text: str) -> str:
    tokens = text.split()
    a, b = int(tokens[0]), int(tokens[1])

    if _losing(a, b):
        return "LOSE"

    # 字典序最小: 先枚举 i 从 0 起, 再枚举 j, 找到第一个使 (a-i, b-j) 为必败态的着法
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            # 合法着法: 单堆取 (i>0,j==0 或 i==0,j>0) 或两堆同取 (i==j)
            if not (j == 0 or i == 0 or i == j):
                continue
            if _losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    # 理论上不会到这里; 保底返回 LOSE
    return "LOSE"
