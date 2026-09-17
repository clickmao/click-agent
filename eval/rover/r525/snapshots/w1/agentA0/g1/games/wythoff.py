"""Wythoff 博弈: 必败点判定与字典序最小必胜着法。"""


def _cold(maxv: int):
    """必败位置 (冷位置) 集合。

    Wythoff 冷位置: 第 n 个冷位置 (n>=0) 为 (a_n, b_n),
    其中 a_n = 未出现过的最小非负整数, b_n = a_n + n。
    这里按 a<=b 存储, 且只保留两坐标均 <= maxv 的位置。
    """
    cold = set()
    used = set()
    n = 0
    while True:
        # 找未使用的最小非负整数
        a = 0
        while a in used:
            a += 1
        b = a + n
        if a > maxv or b > maxv:
            # 由于 a 单调不减, 一旦 b>maxv 仍可能有更大 n 的 a 超过 maxv;
            # 只要 a>maxv 即可停止
            if a > maxv:
                break
        if b <= maxv:
            cold.add((a, b))
        used.add(a)
        used.add(b)
        n += 1
        if a > maxv:
            break
    return cold


def solve(text: str) -> str:
    toks = text.split()
    a = int(toks[0])
    b = int(toks[1])

    cold = _cold(max(a, b))
    lo, hi = (a, b) if a <= b else (b, a)
    if (lo, hi) in cold:
        return "LOSE"

    # 枚举所有 (i, j): i 从第一堆取, j 从第二堆取, 字典序最小
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # 合法着法: 单堆取 或 两堆等量取
            if (i == 0 or j == 0) or (i == j):
                na, nb = a - i, b - j
                if na < 0 or nb < 0:
                    continue
                x, y = (na, nb) if na <= nb else (nb, na)
                if (x, y) in cold:
                    return "WIN %d %d" % (i, j)
    return "LOSE"
