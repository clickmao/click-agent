"""Subtraction game (normal play): WIN with numerically smallest winning move, or LOSE.

Input text:
    line 1: n k
    line 2: k distinct allowed step sizes (contains 1)
Output text: 'WIN m' or 'LOSE'.
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    head = lines[0].split() if lines else []
    if len(head) < 2:
        return 'LOSE'
    n, k = (int(x) for x in head[:2])
    second = lines[1].split() if len(lines) > 1 else []
    allowed = sorted({int(x) for x in second[:k]})
    win = [False] * (n + 1)
    for i in range(1, n + 1):
        for s in allowed:
            if s > i:
                break
            if not win[i - s]:
                win[i] = True
                break
    if not win[n]:
        return 'LOSE'
    for s in allowed:
        if s <= n and not win[n - s]:
            return 'WIN %d' % s
    return 'LOSE'
