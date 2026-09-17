def solve(text: str) -> str:
    nums = list(map(int, text.split()))
    m = nums[0]
    piles = nums[1:1 + m]
    total = 0
    for x in piles:
        total ^= x
    if total == 0:
        return 'LOSE'
    for i in range(m):
        want = piles[i] ^ total
        if want < piles[i]:
            return 'WIN %d %d' % (i + 1, piles[i] - want)
    return 'LOSE'
