"""取石子游戏：每步取走恰好某个允许数目，取走最后一颗者胜。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    steps = sorted(map(int, lines[1].split()))

    # win[i] = 剩 i 颗时轮到当前玩家是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(s <= i and not win[i - s] for s in steps)

    if not win[n]:
        return "LOSE"
    # 数值最小的必胜首取数：取走后对手处于必败态
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
