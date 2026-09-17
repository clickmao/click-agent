"""取石子子游戏: 必败/必胜判定。

入参 text: 第一行 "n k"; 第二行 k 个互不相同的可选步数。
返回: "WIN m" (m = 最小必胜首取数) 或 "LOSE"。
"""


def solve(text: str) -> str:
    lines = [ln for ln in text.split("\n") if ln.strip() != ""]
    n, k = (int(x) for x in lines[0].split())
    steps = [int(x) for x in lines[1].split()][:k]

    # win[i] = 当前有 i 颗石子、轮到行动者的胜负
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in steps)

    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
