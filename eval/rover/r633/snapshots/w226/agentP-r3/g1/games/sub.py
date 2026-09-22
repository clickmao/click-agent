"""取石子子游戏: 先手必胜/必败判定, 必胜时给出数值最小的首取数。

stdin 规格: 第一行 n k; 第二行 k 个互不相同的整数 s1..sk (含 1)。
"""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = [int(t) for t in tokens[2:2 + k]]

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
