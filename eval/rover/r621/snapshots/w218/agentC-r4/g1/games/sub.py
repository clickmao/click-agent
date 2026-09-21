"""取石子子游戏: 判定先手胜负并给出数值最小的必胜首取数。

stdin: 首行 "n k"; 第二行 k 个互不相同的可取数目 (含 1)。
stdout: "WIN m" 或 "LOSE", 末尾不带换行。
"""


def solve(text):
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = [int(t) for t in tokens[2:2 + k]]
    # win[i] = 先手面对 i 颗石子是否必胜。
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        ok = False
        for s in steps:
            if s <= i and not win[i - s]:
                ok = True
                break
        win[i] = ok
    if not win[n]:
        return "LOSE"
    best = None
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            best = s
            break
    return "WIN %d" % best
