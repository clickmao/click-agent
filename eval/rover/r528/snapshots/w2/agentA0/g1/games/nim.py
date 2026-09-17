"""多堆 Nim 必胜手。

输入文本 (stdin 全部):
    第一行: m   (1<=m<=4 石子堆数)
    第二行: m 个整数 a1..am (1<=ai<=15)

玩法: 每次从某一堆取走任意正数目 (不跨堆, 不超该堆现有数), 取走最后一颗者胜。
输出: 先手必胜 -> 一行 `WIN p r` (p 为必胜着法中堆号最小者, 1 起; r 为取走数);
      先手必败 -> 一行 `LOSE`。末尾不带换行。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'

    # 堆号最小者: 找到第一堆 a, 使其变为 a ^ x 更小
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN {} {}'.format(idx + 1, a - target)
    return 'LOSE'  # 不可达
