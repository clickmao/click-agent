"""Subtraction game: WIN m / LOSE.

stdin format:
    n k
    k distinct numbers s1..sk
"""


def solve(text: str) -> str:
    nums = text.split()
    if not nums:
        return ''
    n = int(nums[0])
    k = int(nums[1])
    steps = [int(x) for x in nums[2:2 + k]]

    # win[i] = True if the player to move with i stones wins
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s <= i and not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return 'LOSE'
    best = None
    for s in sorted(steps):
        if s <= n and not win[n - s]:
            best = s
            break
    return 'WIN %d' % best
