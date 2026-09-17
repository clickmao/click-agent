"""取石子子游戏：先手必胜输出 `WIN m`（最小必胜首取），否则 `LOSE`。"""


def solve(text: str) -> str:
    tokens = text.split()
    n = int(tokens[0])
    k = int(tokens[1])
    steps = sorted(int(x) for x in tokens[2:2 + k])

    # win[i] = 当前有 i 颗石子时，行动方是否有必胜策略
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
    # 求数值最小的必胜首取数：取 s 后使对手必败
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    # 理论上不可达
    return "LOSE"
