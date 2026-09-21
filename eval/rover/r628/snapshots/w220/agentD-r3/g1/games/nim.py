def solve(text: str) -> str:
    nums = text.split()
    m = int(nums[0])
    piles = [int(x) for x in nums[1:1 + m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i in range(m):
        a = piles[i]
        need = a ^ x
        if need < a:
            return 'WIN %d %d' % (i + 1, a - need)
    return 'LOSE'
