"""取石子子游戏：判定先手必胜/必败并给出数值最小必胜首取。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    n, k = (int(x) for x in lines[0].split())
    steps = sorted(int(x) for x in lines[1].split()[:k])
    win = [False] * (n + 1)
    for t in range(1, n + 1):
        for s in steps:
            if s <= t and not win[t - s]:
                win[t] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
