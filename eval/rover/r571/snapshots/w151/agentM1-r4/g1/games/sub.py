"""取石子子游戏：先手必败/必胜判定 + 数值最小的必胜首取数。"""


def solve(text: str) -> str:
    lines = text.split()
    n = int(lines[0])
    k = int(lines[1])
    moves = [int(x) for x in lines[2:2 + k]]
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
