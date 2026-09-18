"""取石子：必胜/必败判定，输出数值最小的必胜首取数。

solve(text): 首行 n k；第二行 k 个互不相同的整数 s1..sk（含 1）。
"""


def solve(text):
    toks = text.split()
    n = int(toks[0])
    k = int(toks[1])
    steps = sorted(int(t) for t in toks[2:2 + k])
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
