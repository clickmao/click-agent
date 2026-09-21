"""多堆 Nim: 必胜着法 (最小堆号)。

输入首行: m (1<=m<=4)
第二行: m 个整数 a1..am (1<=ai<=15)
每次从某一堆取走任意正数目的石子, 取走最后一颗者胜。
输出: 先手必胜则 'WIN p r' (p 为堆号最小的必胜着法所在堆, r 为取走数),
      否则 'LOSE'。
"""


def solve(text: str) -> str:
    nums = [int(tok) for tok in text.replace('\n', ' ').replace('\r', ' ').split()]
    m = nums[0]
    piles = list(nums[1:1 + m])

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            take = a - target
            return 'WIN %d %d' % (idx + 1, take)
    return 'LOSE'
