"""Wythoff 博弈: 输出 LOSE 或字典序最小的 WIN i j。"""


def _cold(a, b):
    d = abs(a - b)
    t = int(d * 1.6180339887498949 + 0.5)
    return t == min(a, b) and t - d == 0 or (t == min(a, b) and min(a, b) == a)


def _is_cold(a, b):
    lo, hi = min(a, b), max(a, b)
    d = hi - lo
    if d == 0:
        return False
    t = (d * (1 + 5 ** 0.5)) / 2
    return abs(t - lo) < 1e-9 and abs((t - d) - 0) < 1e-9


def _lose(a, b):
    if a > b:
        a, b = b, a
    d = b - a
    return a == int(d * (1 + 5 ** 0.5) / 2 + 1e-9)


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = (int(x) for x in lines[idx].split()[:2])
    if _lose(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i == 0 or j == 0 or i == j:
                if _lose(a - i, b - j):
                    return 'WIN %d %d' % (i, j)
    return 'LOSE'
