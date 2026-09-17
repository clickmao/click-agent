"""多堆 Nim 必胜手。

规则: 每次从某一堆取走任意正数目的石子, 取走最后一颗者胜。
solve(text) 内 text 为完整 stdin 文本:
  第一行: m  (1<=m<=4 堆数)
  第二行: m 个整数 a1..am (1<=ai<=15 每堆石子数)
返回: 先手必胜 -> "WIN p r" (p 为堆号最小者, 从 1 开始; r 为取走石子数);
      先手必败 -> "LOSE"。
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = list(map(int, lines[1].split()[:m]))
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"
    # 从编号最小的堆开始, 首个存在制胜着法的堆即最小堆号
    for idx, a in enumerate(piles):
        target = a ^ xor          # 目标剩余数 = a ^ 总异或
        if target < a:
            return "WIN %d %d" % (idx + 1, a - target)
    return "LOSE"
