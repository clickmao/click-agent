"""Subtraction game: report the smallest winning first move, or LOSE."""


def solve(text: str) -> str:
    nums = text.split()
    n, k = int(nums[0]), int(nums[1])
    moves = sorted(int(x) for x in nums[2:2 + k])

    # win[i] = True if the player to move with i stones can force a win.
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in moves:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break

    if not win[n]:
        return "LOSE"
    for s in moves:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
