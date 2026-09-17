"""多堆 Nim：输出必胜手 (堆号最小, 每堆至多一个必胜着法) 或 LOSE。

读入: 第一行 m; 第二行 m 个石子堆大小。
输出: "WIN p r" 或 "LOSE"。
"""


def solve(text: str) -> str:
    nums = text.split()
    m = int(nums[0])
    a = [int(x) for x in nums[1:1 + m]]

    xor_all = 0
    for v in a:
        xor_all ^= v
    if xor_all == 0:
        return 'LOSE'

    for i in range(m):
        target = a[i] ^ xor_all
        if target < a[i]:
            return 'WIN %d %d' % (i + 1, a[i] - target)
    return 'LOSE'
