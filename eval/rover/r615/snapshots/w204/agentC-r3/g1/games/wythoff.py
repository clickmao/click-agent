"""Wythoff 博弈：必败点判定与字典序最小的必胜着法。

solve(text) 读入一行 "a b"（两堆石子数，1<=a,b<=25）。
必败输出 "LOSE"；否则输出 "WIN i j"，其中 (i, j) 为全部必胜着法中字典序最小者
（i, j >= 0 且不同时为 0）。

必败点 (a,b) 当且仅当 a = floor(n*phi)、b = a + n（或交换两堆）时成立。
"""


def _is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    # a <= b
    diff = b - a
    x = (diff * (1 + 5 ** 0.5) / 2)
    n = int(x)
    for cand in (n - 1, n, n + 1):
        if cand < 0:
            continue
        if int(cand * (1 + 5 ** 0.5) / 2) == a and a + cand == b:
            return True
    return False


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while lines[idx].strip() == "":
        idx += 1
    parts = lines[idx].split()
    a, b = int(parts[0]), int(parts[1])

    if _is_losing(a, b):
        return "LOSE"

    best = None
    # 着法 (i, j)：从第一堆取 i，从第二堆取 j，i,j>=0 且不同时为 0
    # 候选集合：单堆取（i>0,j=0 或 i=0,j>0）与等量双取（i=j>0）
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            ok = False
            if i == 0 or j == 0:
                ok = True
            elif i == j:
                ok = True
            if not ok:
                continue
            if _is_losing(a - i, b - j):
                cand = (i, j)
                if best is None or cand < best:
                    best = cand
                # i 已递增：同一 i 下更小的 j 后面才出现，需继续扫 j
    assert best is not None
    return "WIN %d %d" % (best[0], best[1])
