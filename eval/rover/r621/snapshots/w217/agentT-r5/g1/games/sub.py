"""取石子游戏: 必胜/必败判定与最小必胜首取。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = (int(x) for x in lines[idx].split())
    idx += 1
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    moves = [int(x) for x in lines[idx].split()][:k]
    moves = sorted(set(moves))
    win = [False] * (n + 1)
    for stones in range(1, n + 1):
        for s in moves:
            if s > stones:
                break
            if not win[stones - s]:
                win[stones] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN ' + str(s)
    return 'LOSE'
