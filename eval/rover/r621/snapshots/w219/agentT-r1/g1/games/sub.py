"""取石子子游戏: 判定先手胜负并给出数值最小的必胜首取数。

输入文本格式:
    第一行: n k
    第二行: k 个互不相同的整数 s1..sk
输出: 'WIN m' 或 'LOSE', 末尾不带换行。
"""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = sorted(int(t) for t in tokens[2:2 + k])

    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s > x:
                break
            if not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
