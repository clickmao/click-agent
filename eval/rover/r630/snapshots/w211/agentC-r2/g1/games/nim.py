"""多堆 Nim: 必胜手 (堆号最小, 取走数目)。

输入文本格式:
    第一行: m  (1<=m<=4 石子堆数)
    第二行: m 个整数 a1..am (1<=ai<=15)

规则: 每次从某一堆取走任意正数目的石子, 取走最后一颗者胜。
输出: 必胜 -> 'WIN p r' (p 为堆号最小的必胜着法的堆号, 堆号从 1 开始;
      r 为从该堆取走的石子数, 每堆至多存在一个必胜着法); 必败 -> 'LOSE'。
"""


def solve(text):
    lines = text.splitlines()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]
    xor_sum = 0
    for a in piles:
        xor_sum ^= a
    if xor_sum == 0:
        return 'LOSE'
    for idx, a in enumerate(piles):
        target = a ^ xor_sum
        if target < a:
            return 'WIN ' + str(idx + 1) + ' ' + str(a - target)
    return 'LOSE'
