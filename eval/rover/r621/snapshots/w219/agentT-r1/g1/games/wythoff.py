"""Wythoff 博弈: 判定必败点, 否则给出字典序最小的必胜着法。

输入文本格式:
    一行: a b
输出: 'LOSE' 或 'WIN i j', 末尾不带换行。
"""


def _pairs(limit: int):
    """Beatty 序列给出的 Wythoff 必败点对, 值不超过 limit。"""
    res = []
    n = 0
    while True:
        x = (n * 5 ** 0.5 + n) // 2
        x = int(x)
        y = x + n
        if x > limit:
            break
        res.append((x, y))
        n += 1
    return res


def _is_cold(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    for x, y in _pairs(max(a, b) + 1):
        if x == a and y == b:
            return True
    return False


def solve(text: str) -> str:
    tokens = text.split()
    a = int(tokens[0])
    b = int(tokens[1])

    best = None
    # 从第一堆取 i 颗 (i 从 0 到 a), 第二堆取 j 颗 (j 从 0 到 b), 不同时为 0
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if _is_cold(na, nb):
                best = (i, j)
                break
        if best is not None:
            break

    if best is None:
        return "LOSE"
    return "WIN " + str(best[0]) + " " + str(best[1])
