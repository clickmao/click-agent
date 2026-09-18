"""取石子子游戏必败/必胜判定。"""


def solve(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    n, k = map(int, lines[0].split())
    steps = sorted(int(x) for x in lines[1].split())
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
            return "WIN %d" % s
    return "LOSE"
