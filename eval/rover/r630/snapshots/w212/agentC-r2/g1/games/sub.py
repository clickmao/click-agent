"""Subtraction game: who wins, and smallest winning first move."""


def solve(text):
    nums = text.split()
    n = int(nums[0])
    k = int(nums[1])
    moves = sorted(set(int(x) for x in nums[2:2 + k]))
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        for s in moves:
            if s <= x and not win[x - s]:
                win[x] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in moves:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
