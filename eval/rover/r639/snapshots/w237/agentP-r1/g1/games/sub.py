"""取石子: 必败/必胜判定, 必胜时给出数值最小的首取数。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    n, k = map(int, lines[0].split())
    moves = sorted(int(x) for x in lines[1].split()[:k])
    moves = [m for m in moves if 1 <= m <= n]
    # win[i] = 剩余 i 颗时轮到行动的一方是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(m <= i and not win[i - m] for m in moves)
    if not win[n]:
        return "LOSE"
    for m in moves:
        if m <= n and not win[n - m]:
            return "WIN %d" % m
    return "LOSE"
