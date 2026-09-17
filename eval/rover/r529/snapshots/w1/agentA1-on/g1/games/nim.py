"""多堆 Nim 必胜首着。

规格:
  第一行: m  (1<=m<=4 石子堆数)
  第二行: m 个整数 a1..am (1<=ai<=15)
玩法: 每次从某一堆取走任意正数目石子, 取走最后一颗者胜。
输出: 先手必胜 -> "WIN p r" (p 为堆号最小的必胜着法堆号, 从 1 起; r 为取走数,
      每堆至多一个必胜着法); 先手必败 -> "LOSE"。

判定: 各堆异或和 (nim-sum) 非零则先手必胜; 对每堆求能否化为使异或和变零。
"""
import functools


def solve(text: str) -> str:
    """纯函数: stdin 文本 -> stdout 文本 (不带末尾换行)。"""
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    total = functools.reduce(lambda a, b: a ^ b, piles, 0)
    if total == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        target = a ^ total          # 使该堆变为 target 后整体异或和为 0
        if target < a:              # 需取走 a-target (正数)
            return 'WIN %d %d' % (i + 1, a - target)
    return 'LOSE'                   # 逻辑上不可达
