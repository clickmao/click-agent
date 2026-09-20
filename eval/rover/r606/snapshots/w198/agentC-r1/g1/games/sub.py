"""取石子子游戏必败/必胜判定。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = map(int, lines[0].split())
    steps = list(map(int, lines[1].split()))[:k]
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in steps:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
