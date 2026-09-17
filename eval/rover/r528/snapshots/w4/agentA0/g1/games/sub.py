"""取石子子游戏: 判定先手必胜/必败, 必胜时给出数值最小的首取数。

状态 n 为剩余石子数, 每步取走允许集合 S 中的某个数目, 取走最后一颗者胜。
必胜条件: 存在 s in S, s <= n 使 n-s 为必败态。
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, _k = (int(x) for x in lines[0].split())
    moves = sorted({int(x) for x in lines[1].split()})
    # win[i] = 剩余 i 颗时先手是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:  # moves 已升序 -> 首个可行者即数值最小
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'  # 理论不可达
