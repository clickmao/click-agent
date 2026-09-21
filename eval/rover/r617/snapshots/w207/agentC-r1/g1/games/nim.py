def solve(text: str) -> str:
    """多堆 Nim: 必胜输出 'WIN p r' (p 为堆号最小的必胜堆, r 为取走数), 否则 'LOSE'。"""
    nums = text.split()
    m = int(nums[0])
    piles = [int(x) for x in nums[1:1 + m]]
    total = 0
    for a in piles:
        total ^= a
    if total == 0:
        return "LOSE"
    for i in range(m):
        target = piles[i] ^ total
        if target < piles[i]:
            return "WIN %d %d" % (i + 1, piles[i] - target)
    return "LOSE"
