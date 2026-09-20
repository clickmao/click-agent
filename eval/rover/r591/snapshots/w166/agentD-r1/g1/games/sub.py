"""取石子子游戏：先手必胜/必败判定，必胜时给数值最小的首取数。"""


def solve(text):
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    n, k = map(int, lines[idx].split())
    idx += 1
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    moves = list(map(int, lines[idx].split()))[:k]

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
