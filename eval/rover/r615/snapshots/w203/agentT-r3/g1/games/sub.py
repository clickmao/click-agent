"""取石子子游戏：必胜判定与最小必胜首取数。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    s = sorted(map(int, lines[1].split()))
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(t <= i and not win[i - t] for t in s)
    if not win[n]:
        return 'LOSE'
    for t in s:
        if t <= n and not win[n - t]:
            return 'WIN %d' % t
    return 'LOSE'
