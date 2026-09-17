"""取石子子游戏: 先手必胜/必败判定, 必胜时给数值最小的首取数。

位置 n 为必胜当且仅当存在允许步 s 使 n-s 为必败; n=0 为必败(无子可取)。
"""


def solve(text: str) -> str:
    data = text.split()
    n = int(data[0])
    k = int(data[1])
    moves = sorted(int(data[2 + i]) for i in range(k))

    # win[i] = 位置 i 是否先手必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:  # 已升序, 第一个可行的必胜步即数值最小
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
