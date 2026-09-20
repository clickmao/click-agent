"""Subtraction game: n k, then k distinct move sizes."""
import sys


def solve(text: str) -> str:
    nums = text.split()
    n = int(nums[0])
    k = int(nums[1])
    steps = sorted(int(x) for x in nums[2:2 + k])
    win = [False] * (n + 1)
    best = [0] * (n + 1)
    for i in range(1, n + 1):
        for s in steps:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                best[i] = s
                break
    if win[n]:
        return "WIN %d" % best[n]
    return "LOSE"
