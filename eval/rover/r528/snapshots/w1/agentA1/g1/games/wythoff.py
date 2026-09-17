"""Wythoff's game decision: LOSE, or the lexicographically smallest winning move.

A position (a, b) is cold (losing for the mover) iff, with k = b - a >= 0 and
a <= b, it equals (floor(k*phi^2) - k, floor(k*phi^2)); equivalently
a == floor(k*phi). We test this exactly with integer arithmetic:
    floor(k*phi) == a  <=>  a^2 <= k^2 + k*a < (a+1)^2
Rewriting the right bound via a*a + 2a + 1 > k*k + k*a.
"""


def _lose(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    k = b - a
    # exact test of a == floor(k * phi), phi = (1 + sqrt(5)) / 2
    # a <= k*phi  <=>  2a - k <= k*sqrt(5)  (valid since k >= 0)
    lhs = 2 * a - k
    if lhs < 0:
        return False
    if lhs * lhs > 5 * k * k:
        return False
    # a + 1 > k*phi  <=>  2a + 2 - k > k*sqrt(5)
    lhs2 = 2 * a + 2 - k
    if lhs2 <= 0:
        return False
    return lhs2 * lhs2 > 5 * k * k


def solve(text: str) -> str:
    a, b = map(int, text.split()[:2])

    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if _lose(a - i, b - j):
                best = (i, j)
                break
        if best is not None:
            break

    return "LOSE" if best is None else "WIN %d %d" % best
