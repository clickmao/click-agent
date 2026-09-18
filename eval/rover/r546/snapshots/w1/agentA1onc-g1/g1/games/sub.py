"""取石子子游戏 (subtraction game) 必败/必胜判定。

solve(text) 读入:
  第一行 n k  (n 石子数, k 可选步数个数)
  第二行 k 个互不相同整数 s1..sk (含 1), 一次可取走恰好某个允许数目
规则: 取走最后一颗者胜。
输出: 先手必胜 -> 'WIN m' (m 为数值最小的必胜首取数); 否则 -> 'LOSE'。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    n, k = (int(x) for x in lines[0].split())
    steps = sorted(int(x) for x in lines[1].split()[:k])

    # win[i] = 剩余 i 颗时轮到行动者是否必胜
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    # 数值最小的必胜首取数: 取 s 后对手处于必败局面
    for s in steps:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
