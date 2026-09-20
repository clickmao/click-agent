"""取石子子游戏: WIN m / LOSE。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    n, k = (int(x) for x in lines[idx].split())
    idx += 1
    moves = [int(x) for x in lines[idx].split()][:k]

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
            return 'WIN %d' % s
    return 'LOSE'
