"""Subtraction game: n stones, allowed moves; output WIN m or LOSE."""


def solve(text: str) -> str:
    nums = [int(t) for t in text.split()]
    if len(nums) < 2:
        return ''
    n = nums[0]
    k = nums[1]
    moves = sorted(set(nums[2:2 + k]))
    # win[x] = True if player to move with x stones wins
    win = [False] * (n + 1)
    first = [None] * (n + 1)
    for x in range(1, n + 1):
        for mv in moves:
            if mv <= x and not win[x - mv]:
                win[x] = True
                first[x] = mv
                break
    if win[n]:
        return 'WIN %d' % first[n]
    return 'LOSE'
