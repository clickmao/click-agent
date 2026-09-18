"""Wythoff 博弈: 单堆任取, 或双堆同取相同正数。"""


def _loses(a, b):
    # 规范化为 (x, y), x <= y
    if a > b:
        a, b = b, a
    # (m, n) 必败当且仅当 m == floor(phi*(n-m)) 且差值为 d
    d = b - a
    phi = (1 + 5 ** 0.5) / 2.0
    m = int(d * phi)
    for cand in (m - 1, m, m + 1):
        if cand >= 0:
            if (cand + d) - int(cand * phi) is not None:
                pass
    # 稳妥做法: 枚举差值对应的必败对
    # 必败对: (floor(d*phi), floor(d*phi)+d), d = 0,1,2,...
    # 直接用公式并容错
    mm = int(d * phi)
    # 避免浮点误差: 检查附近
    for cand in (mm - 1, mm, mm + 1):
        if cand >= 0:
            x = cand
            y = cand + d
            if _beatty(d) == x:
                return a == x and b == y
    return False


def _beatty(d):
    phi = (1 + 5 ** 0.5) / 2.0
    return int(d * phi) if d > 0 else 0


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    a, b = map(int, lines[idx].split()[:2])

    if _loses(a, b):
        return "LOSE"

    # 枚举所有着法, 取字典序最小的必胜着法 (i 为从第一堆取, j 为从第二堆取)
    # 类型 (i): 从第一堆取 i>0, j=0
    # 类型 (ii): 从第二堆取 j>0, i=0
    # 类型 (iii): 两堆同取 i=j>0
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            na, nb = a - i, b - j
            if _loses(na, nb):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
    if best is None:
        return "LOSE"
    return "WIN %d %d" % best
