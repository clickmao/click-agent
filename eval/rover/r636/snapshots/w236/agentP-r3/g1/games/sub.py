"""取石子游戏：判定先手胜负并给出数值最小的必胜首取数。

入参：完整 stdin 文本；返回：'WIN m' 或 'LOSE'，末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    n, _k = int(lines[0].split()[0]), int(lines[0].split()[1])
    moves = sorted(int(x) for x in lines[1].split())
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
