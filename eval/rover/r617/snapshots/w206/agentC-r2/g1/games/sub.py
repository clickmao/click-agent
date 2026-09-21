"""Subtraction game: win/lose and the smallest winning first move.

stdin: first line "n k" (1<=n<=80, 1<=k<=12), second line k distinct step sizes
(1<=si<=12, always contains 1).
Output: "WIN m" with the numerically smallest winning first move, or "LOSE".
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    n, k = (int(v) for v in lines[0].split())
    steps = sorted(int(v) for v in lines[1].split())[:k]
    win = [False] * (n + 1)
    for x in range(1, n + 1):
        win[x] = any(s <= x and not win[x - s] for s in steps)
    if not win[n]:
        return "LOSE"
    for s in steps:
        if s <= n and not win[n - s]:
            return "WIN %d" % s
    return "LOSE"
