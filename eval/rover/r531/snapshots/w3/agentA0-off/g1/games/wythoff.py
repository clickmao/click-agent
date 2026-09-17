"""Wythoff 博弈: 必败点判定 + 约定序下的最小必胜着法。

必败点 (冷点) 递推构造, 无浮点:
    第 n 个冷点 = (p_n, p_n + n), p_n 是尚未被使用的最小非负整数。

胜负判定: 两堆同时为 0 的一方获胜 => 轮到 (0,0) 者必败, 冷点即必败态。

着法枚举顺序 (由公开用例反推, 两例共用一条规则):
    21 25 -> (15, 15)   ; 21-15=6,  25-15=10  -> 冷点 (6,10)
    10  9 -> ( 0,  3)   ; 10-0=10,   9- 3= 6  -> 冷点 (10,6)
    注意 (8,8) 也是 10 9 的合法必胜着法 (剩余 (2,1) 为冷点),
    但样例取 (0,3):  两例一致符合 **i + j 最小**。
    (0,3): i+j=3 最小; (15,15): 21 25 下唯一着法。
"""


def _build_cold(limit):
    """递推构造 max 坐标 <= limit 的冷点集合 (对称收录)。"""
    used = set()
    cold = set()
    n = 0
    while True:
        p = 0
        while p in used:
            p += 1
        q = p + n
        if q > limit:
            break
        used.add(p)
        used.add(q)
        cold.add((p, q))
        cold.add((q, p))
        n += 1
    return cold


_CACHE = {}


def _is_losing(a, b):
    limit = 64
    if limit not in _CACHE:
        _CACHE[limit] = _build_cold(limit)
    return (a, b) in _CACHE[limit]


def _legal(i, j, a, b):
    if i == 0 and j == 0:
        return False
    if i > a or j > b:
        return False
    # (i) 只动一堆 或 (ii) 两堆同取
    return (i == 0) or (j == 0) or (i == j)


def solve(text: str) -> str:
    lines = text.splitlines()
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = (int(x) for x in lines[idx].split()[:2])

    if _is_losing(a, b):
        return 'LOSE'

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if not _legal(i, j, a, b):
                continue
            if not _is_losing(a - i, b - j):
                continue
            key = (i + j, i, j)  # i+j 最小, 同和时 i 最小
            if best is None or key < best[0]:
                best = (key, i, j)
    return 'WIN %d %d' % (best[1], best[2])
