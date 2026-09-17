"""Wythoff 博弈：必败点输出 `LOSE`，否则输出字典序最小的必胜着法 `WIN i j`。"""


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    # 计算必败点 (cold positions)：P_n = (floor(n*phi), floor(n*phi^2))
    # 用整数递推：beatty 序列互补判定
    cold = set()
    # a,b <= 25，n 取到足够大即可
    for n in range(0, 60):
        # floor(n * (1+sqrt(5))/2)
        x = _beatty(n, 1)
        y = x + n
        if x > 25 and y > 25:
            break
        cold.add((x, y))

    if (a, b) in cold or (b, a) in cold:
        return "LOSE"

    best = None
    # (i, j): 从第一堆取 i，第二堆取 j
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # 必须为合法着法：或取同一堆任意正数（另一堆不动），或两堆同取相同正数
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if (na, nb) in cold or (nb, na) in cold:
                if best is None or (i, j) < best:
                    best = (i, j)
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best


def _beatty(n: int, mul: int) -> int:
    # floor(n * (1+sqrt(5))/2) 的精确整数实现：
    # 用连分数/整数牛顿法求 isqrt 版本：floor(n*phi) = (n + n*isqrt(5)) // 2 不精确，
    # 改用精确方法：找到最大 x 使 x*2 <= n*(1+sqrt5) 等价于 (2x-n)^2 <= 5 n^2 且 2x>=n
    if n == 0:
        return 0
    from math import isqrt
    # 求 ceil(n*sqrt(5)) 的下界：floor(n*phi) = (n + floor(n*sqrt5))/2 是否成立需验证
    # 直接精确：max x s.t. x < n*phi  => x = floor(n*phi)
    # 用整数比较：x <= floor(n*phi) <=> 2x - n <= n*sqrt5 <=> (2x-n) >= 0 且 (2x-n)^2 <= 5 n^2
    s5 = isqrt(5 * n * n)
    # floor(n*sqrt5) = s5（因为 5n^2 非完全平方，isqrt 向下取整正好）
    val = (n + s5) // 2
    # 校验并微调（防御性）
    while _sq(2 * (val + 1) - n) <= 5 * n * n:
        val += 1
    while val > 0 and _sq(2 * val - n) > 5 * n * n:
        val -= 1
    return val


def _sq(x: int) -> int:
    return x * x
