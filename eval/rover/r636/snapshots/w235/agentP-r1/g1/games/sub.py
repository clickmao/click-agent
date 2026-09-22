"""取石子子游戏: 必胜/必败判定。"""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = [int(x) for x in lines[0].split()]
    s = sorted(int(x) for x in lines[1].split())
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for move in s:
            if move > i:
                continue
            if not win[i - move]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for move in s:
        if move <= n and not win[n - move]:
            return 'WIN %d' % move
    return 'LOSE'
