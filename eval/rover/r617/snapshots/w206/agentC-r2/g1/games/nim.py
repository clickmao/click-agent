"""Multi-pile Nim: smallest-index winning move.

stdin: first line m (1<=m<=4), second line m pile sizes (1<=ai<=15).
Output: "WIN p r" (p = smallest 1-based pile index with a winning reduction,
r = stones removed from it), or "LOSE".
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    m = int(lines[0])
    piles = [int(v) for v in lines[1].split()][:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return "WIN %d %d" % (i + 1, a - target)
    return "LOSE"
