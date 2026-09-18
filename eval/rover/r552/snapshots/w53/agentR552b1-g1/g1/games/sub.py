"""取石子游戏：先手必胜/必败判定（每步取走恰好某个允许的数目）。"""


def solve(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    n, _k = map(int, lines[0].split())
    steps = sorted(set(int(x) for x in lines[1].split()))
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
