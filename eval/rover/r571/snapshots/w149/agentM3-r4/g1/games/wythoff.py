"""Wythoff game: cold (P-)position detection and lexicographically smallest winning move.

A position (a, b) is a losing position for the player to move exactly when
{a, b} == {floor(phi*n), floor(phi*phi*n)} for some n >= 0.  Otherwise the
winning moves are enumerated over allowed move types and emitted in the
lexicographically smallest (i, j) order required by the statement.
"""

PHI = (1.0 + 5.0 ** 0.5) / 2.0


def _is_cold(a: int, b: int) -> bool:
    x, y = (a, b) if a <= b else (b, a)
    n = int((y - x) / PHI)
    for m in range(max(0, n - 2), n + 3):
        if m < 0:
            continue
        if (int(m * PHI), int(m * PHI * PHI)) == (x, y):
            return True
    return False


def solve(text: str) -> str:
    a, b = (int(x) for x in text.split()[:2])
    if _is_cold(a, b):
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            rest_a, rest_b = a - i, b - j
            legal = (i == 0 or j == 0) or (i == j)
            if legal and (rest_a == 0 and rest_b == 0 or _is_cold(rest_a, rest_b)):
                return "WIN %d %d" % (i, j)
    return "LOSE"
