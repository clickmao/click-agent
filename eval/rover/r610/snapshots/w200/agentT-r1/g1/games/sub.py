"""sub: 取石子子游戏必胜/必败判定。

输入格式：
    第一行 n k（n 为石子数，k 为可选步数个数）
    第二行 k 个互不相同的整数 s1..sk（每步可取走的石子数）
输出：WIN m（m 为数值最小的必胜首取数）或 LOSE。
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    n = int(first[0])
    moves = sorted(int(x) for x in lines[1].split())

    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
