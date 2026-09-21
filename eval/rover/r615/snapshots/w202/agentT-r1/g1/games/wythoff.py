"""Wythoff 博弈: 判定先手胜负并给出字典序最小的必胜着法 (i, j)。"""


def solve(text: str) -> str:
    """输入完整 stdin 文本, 返回应写出的 stdout 文本(末尾不带换行)。"""
    parts = text.split()
    if not parts:
        return ""
    a, b = int(parts[0]), int(parts[1])

    # 先手必败点 (冷点): (floor(m*phi), floor(m*phi^2)), m >= 0
    cold = set()
    phi = (1 + 5 ** 0.5) / 2
    for m in range(0, 30):
        p = int(m * phi)
        q = int(m * phi * phi)
        if q > 60 and p > 60:
            break
        cold.add((p, q))
        cold.add((q, p))

    if (a, b) in cold:
        return "LOSE"

    best = None
    # 同取: 从两堆同时取 i 颗
    for i in range(1, min(a, b) + 1):
        if (a - i, b - i) in cold:
            cand = (i, i)
            if best is None or cand < best:
                best = cand
    # 只从第一堆取
    for i in range(1, a + 1):
        if (a - i, b) in cold:
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    # 只从第二堆取
    for j in range(1, b + 1):
        if (a, b - j) in cold:
            cand = (0, j)
            if best is None or cand < best:
                best = cand

    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
