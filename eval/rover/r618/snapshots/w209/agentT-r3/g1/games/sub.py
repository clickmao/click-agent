"""取石子子游戏：判定必胜/必败并给最小必胜首取数。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = (int(x) for x in lines[0].split())
    steps = [int(x) for x in lines[1].split()]
    steps = list(steps)[:k]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    best = None
    for s in steps:
        if s <= n and not win[n - s]:
            if best is None or s < best:
                best = s
    return 'WIN %d' % best
