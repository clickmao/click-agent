"""Wythoff's game: lexicographically smallest winning (i, j).

stdin: one line "a b" (1<=a<=25, 1<=b<=25).
Output: "WIN i j" (i from pile 1, j from pile 2, lexicographically smallest, not both 0),
or "LOSE".
"""

_COLD = set()
_m = 0
_n = 0

def _extend(limit):
    global _m, _n
    while _n <= limit:
        _m += 1
        _n = _m + 1 if _m == 0 else _n + 1
    return


def _build(upto):
    cold = set()
    used = set()
    n = 0
    while True:
        a = n * (1 + 5 ** 0.5) / 2.0
        x = int(a + 1e-9)
        y = x + n
        if x > upto:
            break
        cold.add((x, y))
        cold.add((y, x))
        n += 1
    return cold


def solve(text: str) -> str:
    a, b = (int(v) for v in text.split()[:2])
    cold = _build(30)
    if (a, b) in cold:
        return "LOSE"
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if (a - i, b - j) in cold:
                return "WIN %d %d" % (i, j)
    return "LOSE"
