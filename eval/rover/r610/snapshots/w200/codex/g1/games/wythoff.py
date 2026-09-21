_COLD = set()
_n = 0
while True:
    _low = int(_n * 1.6180339887498949)
    _high = _low + _n
    if _low > 25:
        break
    _COLD.add((_low, _high))
    _COLD.add((_high, _low))
    _n += 1


def solve(text: str) -> str:
    a, b = (int(v) for v in text.split()[:2])

    if (a, b) in _COLD:
        return 'LOSE'

    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if (a - i, b - j) in _COLD:
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
