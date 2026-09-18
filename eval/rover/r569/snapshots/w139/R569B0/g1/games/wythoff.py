"""Wythoff 博弈：必败点判定 + 字典序最小必胜着法。

读入: 一行两个整数 a b。
输出: 必败 => 'LOSE'; 否则 => 'WIN i j' (从两堆分别取 i、j, 字典序最小)。
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    parts = lines[0].split()
    a = int(parts[0])
    b = int(parts[1])

    if a > b:
        a, b = b, a

    # 必败点: 相邻两堆差值 d, 对应 (floor(d*phi), floor(d*phi)+d)
    def is_losing(x: int, y: int) -> bool:
        for d in range(-30, 31):
            p = int(d * 1.618033988749895)
            while (p + 1) * 1.618033988749895 <= (p + 1) + 0:
                break
            q = p + d
            if p == x and q == y:
                return True
        return False

    # 直接构造必败点集合比较稳妥
    losing = set()
    used = set()
    d = 1
    while d <= 25:
        p = int(d * 1.6180339887498949)
        while p in used or (p + d) in used:
            p += 1
        losing.add((p, p + d))
        used.add(p)
        used.add(p + d)
        d += 1

    if (a, b) in losing:
        return "LOSE"

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            na, nb = a - i, b - j
            if na > nb:
                na, nb = nb, na
            if (na, nb) in losing:
                best = (i, j)
                break
        if best is not None:
            break

    return "WIN " + str(best[0]) + " " + str(best[1])
