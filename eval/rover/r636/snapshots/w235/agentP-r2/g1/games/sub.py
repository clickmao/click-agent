"""取石子: 必败/必胜判定, 输出最小必胜首取数。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    first = lines[0].split()
    n = int(first[0])
    steps = sorted(set(int(x) for x in lines[1].split()))
    win = [False] * (n + 1)
    win[0] = False
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
