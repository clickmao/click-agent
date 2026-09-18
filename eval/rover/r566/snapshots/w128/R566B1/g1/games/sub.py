"""取石子游戏: 允许步数集合 s, 每步取走恰好一个允许数目。"""


def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    n, k = map(int, lines[idx].split()[:2])
    idx += 1
    moves = []
    while idx < len(lines) and len(moves) < k:
        moves.extend(int(x) for x in lines[idx].split())
        idx += 1
    moves = moves[:k]

    # win[x] = True 表示剩余 x 颗时的当前行动者必胜
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s <= x and not win[x - s]:
                win[x] = True
                break

    if not win[n]:
        return "LOSE"
    best = None
    for s in moves:
        if s <= n and not win[n - s]:
            if best is None or s < best:
                best = s
    return "WIN %d" % best
