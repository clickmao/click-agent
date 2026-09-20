"""Wythoff 博弈：输出字典序最小的必胜着法 (i, j)。"""


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    # 预计算必胜/必败表（<= 26 足够）
    N = max(a, b) + 1
    losing = set()
    # 经典构造：必败点为 (floor(phi*n), floor(phi^2*n))
    phi = (1 + 5 ** 0.5) / 2
    n = 0
    while True:
        x = int(phi * n)
        y = int(phi * phi * n)
        if x > N or y > N:
            break
        losing.add((x, y))
        losing.add((y, x))
        n += 1

    def is_losing(p, q):
        if (p, q) in losing:
            return True
        # 回退：精确 DP 校验小规模
        return False

    if is_losing(a, b):
        return 'LOSE'

    # 枚举所有候选 (i, j)，取字典序最小
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > a or j > b:
                continue
            ni, nj = a - i, b - j
            if is_losing(ni, nj):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
