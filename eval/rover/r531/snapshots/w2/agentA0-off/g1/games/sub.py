"""取石子子游戏 (subtraction game) 必胜/必败判定。

规则: 两人轮流取, 每次取走恰好某个允许的数目, 取走最后一颗者胜。
solve(text) 内 text 为完整 stdin 文本:
  第一行: n k  (1<=n<=80 石子数, 1<=k<=12 可选步数个数)
  第二行: k 个互不相同的整数 s1..sk (1<=si<=12, 必含 1)
返回: 先手必胜 -> "WIN m" (m 为数值最小的必胜首取数); 先手必败 -> "LOSE"。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = map(int, lines[0].split())
    moves = sorted(map(int, lines[1].split()[:k]))
    # win[i] = 剩 i 颗时轮到当前行动者是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        win[i] = any(m <= i and not win[i - m] for m in moves)
    if not win[n]:
        return "LOSE"
    # moves 已升序, 首个使对手为必败态的 m 即最小的必胜首取数
    for m in moves:
        if m <= n and not win[n - m]:
            return "WIN %d" % m
    return "LOSE"
