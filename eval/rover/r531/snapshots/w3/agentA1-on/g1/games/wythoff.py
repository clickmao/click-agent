"""Wythoff 博弈: 必败点判定 + 字典序最小的必胜着法。

solve(text) -> str
  入参 text = 完整 stdin 文本: 一行两个整数 a b (两堆石子数)。
  返回: 先手必败 -> "LOSE"; 否则 -> "WIN i j" (从第一堆取 i、第二堆取 j,
        所有必胜着法中按 (i, j) 字典序最小, i,j>=0 且不同时为 0)。

Wythoff 必败点 (P-positions): (floor(k*phi), floor(k*phi^2)), k = 0,1,2,...
当且仅当 (min(a,b), max(a,b)) 形如 (floor(k*phi), floor(k*phi^2)) 时必败。
"""

_PHI = (1.0 + 5.0 ** 0.5) / 2.0


def _is_p_position(a, b):
    if a > b:
        a, b = b, a
    # b - a = k, a = floor(k*phi)
    k = b - a
    if k <= 0:
        return a == 0 and b == 0
    if int(k * _PHI) != a:
        return False
    # 双保险: 高位 floor(k*phi^2) 也须等于 b
    if int(k * _PHI * _PHI) != b:
        return False
    return True


def solve(text: str) -> str:
    data = text.split()
    a = int(data[0])
    b = int(data[1])

    if _is_p_position(a, b):
        return 'LOSE'

    best = None  # (i, j) 字典序最小
    # 类型 (i): 只减第一堆 -> i 从 1..a, j=0
    for i in range(1, a + 1):
        if _is_p_position(a - i, b):
            cand = (i, 0)
            if best is None or cand < best:
                best = cand
    # 类型 (ii): 只减第二堆 -> i=0, j 从 1..b
    for j in range(1, b + 1):
        if _is_p_position(a, b - j):
            cand = (0, j)
            if best is None or cand < best:
                best = cand
    # 类型 (iii): 两堆同减 t -> i=j=t, t 从 1..min(a,b)
    for t in range(1, min(a, b) + 1):
        if _is_p_position(a - t, b - t):
            cand = (t, t)
            if best is None or cand < best:
                best = cand

    return 'WIN %d %d' % best
