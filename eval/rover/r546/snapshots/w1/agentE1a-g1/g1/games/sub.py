"""取石子子游戏必败/必胜判定。"""


def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    steps = [int(x) for x in lines[2:2 + k]]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    best = None
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            best = s
            break
    return "WIN " + str(best)
