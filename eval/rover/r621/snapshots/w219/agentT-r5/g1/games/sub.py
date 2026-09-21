"""取石子子游戏：判定先手胜负并给出数值最小的必胜首取数。

入参 text: 第一行 "n k"；第二行 k 个互不相同整数 s1..sk。
返回: "WIN m" 或 "LOSE"，末尾不带换行。
约定: n 颗石子，每次取走恰好一个允许数目，取走最后一颗者胜。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    n, _k = (int(x) for x in lines[0].split())
    steps = sorted(int(x) for x in lines[1].split())

    # win[i] = 还剩 i 颗石子时轮到行动的一方是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
