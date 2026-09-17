"""取石子子游戏 (减法游戏) 必胜/必败判定。

输入格式:
    第一行: n k   (1<=n<=80 石子数, 1<=k<=12 可选步数个数)
    第二行: k 个互不相同整数 s1..sk (1<=si<=12, 保证含 1)

玩法: 两人轮流取, 每次取走恰好某个允许数目, 取走最后一颗者胜。

输出:
    先手必胜 -> 一行 "WIN m" (m = 数值最小的必胜首取数)
    先手必败 -> 一行 "LOSE"
"""


def _is_win(n, moves, memo):
    """剩余 n 颗时轮到当前行动者是否必胜 (标准博弈 DP)。"""
    if n == 0:
        return False
    if n in memo:
        return memo[n]
    res = any(0 <= n - s and not _is_win(n - s, moves, memo) for s in moves)
    memo[n] = res
    return res


def solve(text: str) -> str:
    parts = text.split()
    n, k = int(parts[0]), int(parts[1])
    moves = sorted(int(x) for x in parts[2:2 + k])
    memo = {}
    for s in moves:
        if s <= n and not _is_win(n - s, moves, memo):
            return "WIN {}".format(s)
    return "LOSE"
