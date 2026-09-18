"""多堆 Nim: 输出必胜着法。

输入格式:
    第一行: m          (1<=m<=4)
    第二行: m 个整数 a1..am (1<=ai<=15)

玩法: 每次从某一堆取走任意正数目的石子, 取走最后一颗者胜。
输出: 先手必胜 -> "WIN p r" (p=堆号最小者, 1 起; r=从该堆取走数);
      先手必败 -> "LOSE"。

依据: Nim 的必败态当且仅当各堆异或和为 0; 必胜着法即把异或和变 0。
"""


def solve(text: str) -> str:
    """纯函数: 入参=完整 stdin 文本, 返回=应写出的 stdout 文本 (不带末尾换行)。"""
    nums = text.split()
    m = int(nums[0])
    piles = [int(x) for x in nums[1:1 + m]]

    x = 0
    for a in piles:
        x ^= a

    if x == 0:
        return "LOSE"

    # 堆号最小者: 取 r = a - (a ^ x) > 0, 使该堆变为 a^x, 整体异或归零
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"  # 理论不可达 (x != 0 必有解)
