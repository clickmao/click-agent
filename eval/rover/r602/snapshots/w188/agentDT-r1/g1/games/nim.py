def solve(text):
    nums = [int(x) for x in text.split()]
    m = nums[0]
    piles = nums[1:1 + m]
    x = 0
    for p in piles:
        x ^= p
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        t = piles[idx] ^ x
        if t < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - t)
    return 'LOSE'
