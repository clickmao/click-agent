"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。

读入: 一行两个整数 a b。
规则: 每次可从任意一堆取走任意正的数目，或从两堆同时取走相同的正的数目。
输出: 'LOSE' 或 'WIN i j'（i,j >= 0 且不同时为 0，按字典序最小）。
"""


def _is_losing(a: int, b: int) -> bool:
    """(a,b) 是否为必败点（Wythoff 公式）。"""
    x, y = (a, b) if a <= b else (b, a)
    # 候选 n = floor(x * phi)，检查是否为 (floor(phi*n), floor(phi^2*n))
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    n = int(x / phi)
    for cand in (n - 1, n, n + 1):
        if cand < 0:
            continue
        if int(cand * phi) == x and int(cand * phi * phi) == y:
            return True
    return False


def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    a, b = (int(t) for t in lines[0].split()[:2])

    if _is_losing(a, b):
        return "LOSE"

    # 枚举全部合法着法，取 (i, j) 字典序最小者
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue  # 只能从一堆取，或两堆取相同数目
            if _is_losing(a - i, b - j):
                return "WIN %d %d" % (i, j)
    return "LOSE"
