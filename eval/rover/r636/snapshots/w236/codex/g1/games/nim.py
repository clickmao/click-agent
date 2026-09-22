def solve(text: str) -> str:
    nums = text.split()
    m = int(nums[0])
    piles = [int(x) for x in nums[1:1 + m]]
    xor = 0
    for a in piles:
        xor ^= a
    if xor == 0:
        return "LOSE"
    for i, a in enumerate(piles):
        target = a ^ xor
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
