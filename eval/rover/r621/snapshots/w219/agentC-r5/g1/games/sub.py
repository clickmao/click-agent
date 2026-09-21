"""取石子子游戏: 判定先手胜负并给出数值最小的必胜首取数。

入参为完整 stdin 文本, 返回应当写出的 stdout 文本(末尾不带换行)。
"""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = [int(tokens[2 + i]) for i in range(k)]

    # win[i] = 剩 i 颗石子时轮到走的人是否有必胜策略
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
            return "WIN " + str(s)
    return "LOSE"
