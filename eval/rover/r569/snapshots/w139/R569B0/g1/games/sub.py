"""取石子子游戏：先手必胜/必败判定 + 最数值最小必胜首取数。

读入: 第一行 n k; 第二行 k 个互不相同的整数 s1..sk (含 1)。
输出: 必胜 => 'WIN m' (m 为数值最小的必胜首取数); 必败 => 'LOSE'。
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    if len(lines) < 2:
        return "LOSE"
    first = lines[0].split()
    n = int(first[0])
    moves = [int(x) for x in lines[1].split()]

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        res = False
        for s in moves:
            if s <= i and not win[i - s]:
                res = True
                break
        win[i] = res

    if not win[n]:
        return "LOSE"

    smallest = None
    for s in sorted(moves):
        if s <= n and not win[n - s]:
            smallest = s
            break
    return "WIN " + str(smallest)
