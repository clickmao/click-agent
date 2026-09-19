_PHI = (1.0 + 5.0 ** 0.5) / 2.0

_LIMIT = 100
_LOSING = set()
for _n in range(1, _LIMIT + 1):
    _p = int(_n * _PHI)
    _q = _p + _n
    _LOSING.add((_p, _q))
    _LOSING.add((_q, _p))


def _is_cold(a: int, b: int) -> bool:
    # 终局 (0, 0) 为必败点（面对它的人已输）
    if a == 0 and b == 0:
        return True
    if a <= 0 or b <= 0:
        return False
    return (a, b) in _LOSING


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _is_cold(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
