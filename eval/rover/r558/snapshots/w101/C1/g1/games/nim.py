def solve(text: str) -> str:
    nums = list(map(int, text.split()))
    m = nums[0]
    heaps = nums[1:1 + m]

    x = 0
    for a in heaps:
        x ^= a

    if x == 0:
        return "LOSE"
    for i in range(m):
        target = heaps[i] ^ x
        if target < heaps[i]:
            return "WIN %d %d" % (i + 1, heaps[i] - target)
    return "LOSE"
