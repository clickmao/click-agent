"""取石子子游戏: 必胜判定与数值最小的必胜首取数。"""


def solve(text: str) -> str:
    tokens = text.split()
    if not tokens:
        return ""
    n = int(tokens[0])
    k = int(tokens[1]) if len(tokens) > 1 else 0
    steps = [int(x) for x in tokens[2:2 + k]]

    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s <= x and not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return "LOSE"
    best = min(s for s in steps if s <= n and not win[n - s])
    return "WIN %d" % best
