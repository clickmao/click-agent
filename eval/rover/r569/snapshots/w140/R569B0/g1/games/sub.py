"""取石子子游戏: 先手必胜/必败判定, 必胜时给出数值最小的首取数。"""


def solve(text):
    lines = text.split("\n")
    second = lines[1].split()
    n = int(lines[0].split()[0])
    steps = [int(x) for x in second]
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
