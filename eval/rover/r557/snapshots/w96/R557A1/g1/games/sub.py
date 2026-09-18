"""取石子子游戏：WIN m / LOSE。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ""
    n, _k = map(int, lines[0].split())
    moves = list(map(int, lines[1].split())) if len(lines) > 1 else [1]
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return "LOSE"
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return "WIN " + str(s)
    return "LOSE"
