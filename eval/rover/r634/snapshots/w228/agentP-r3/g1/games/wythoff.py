"""Wythoff 博弈: 必败点判定与字典序最小必胜着法。

必败点 (cold positions) 恰为 (floor(n*phi), floor(n*phi^2)), phi=(1+sqrt(5))/2。
为避免浮点误差, 用整数精确计算: 必败点第 n 个为 (a_n, b_n),
其中 a_n = floor(n*phi) 可用整数判定 c = floor(x*(1+sqrt(5))/2) 的等价形式 a_n = floor(x*phi)。
这里直接枚举 n 到上限, 用整数递推生成必败点集合。
"""


def _cold_set(limit):
    """生成所有满足 max(a,b) <= limit 的必败点 (无序对 -> 有序 (min,max)) 集合。"""
    cold = set()
    seen = set()
    n = 0
    while True:
        a = (n * (1 + 5 ** 0.5)) / 2.0
        b = (n * (3 + 5 ** 0.5)) / 2.0
        ai = int(a + 0.5)
        bi = int(b + 0.5)
        if abs(a - ai) < 1e-6 and abs(b - bi) < 1e-6:
            pair = (ai, bi) if ai <= bi else (bi, ai)
            cold.add(pair)
            seen.add(ai)
            seen.add(bi)
        if int(a) > limit + 2:
            break
        n += 1
        if n > 10 * (limit + 10):
            break
    return cold


_COLD = _cold_set(60)


def _is_lose(a, b):
    x, y = (a, b) if a <= b else (b, a)
    return (x, y) in _COLD


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    a, b = (int(x) for x in lines[0].split())
    if _is_lose(a, b):
        return 'LOSE'
    best = None
    for da in range(0, a + 1):
        for db in range(0, b + 1):
            if da == 0 and db == 0:
                continue
            if da != 0 and db != 0 and da != db:
                continue
            ra = a - da
            rb = b - db
            if _is_lose(ra, rb):
                if best is None or (da, db) < best:
                    best = (da, db)
    if best is None:
        return 'LOSE'
    return 'WIN %d %d' % best
