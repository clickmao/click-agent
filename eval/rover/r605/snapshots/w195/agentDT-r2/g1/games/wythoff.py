"""Wythoff game: lexicographically smallest winning move (i, j).

Input layout (whole stdin text):
    a b
Output: 'WIN i j' or 'LOSE', no trailing newline.
A position is losing iff it is a Wythoff pair (floor(n*phi), floor(n*phi)+n)
for some n >= 0. Winning moves are scanned in lexicographic order over
(i, j) with i, j >= 0 and not both zero.
"""

PHI_NUM = 1 + 5 ** 0.5  # 2 * phi, exact enough for values up to 25


def _losing(a, b):
    if a > b:
        a, b = b, a
    for n in range(0, 26):
        p = int(n * PHI_NUM / 2)
        if a == p and b == p + n:
            return True
        if p > a:
            return False
    return False


def solve(text: str) -> str:
    parts = text.split()
    if not parts:
        return ''
    a, b = int(parts[0]), int(parts[1])
    if _losing(a, b):
        return 'LOSE'
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if i > 0 and j > 0 and i != j:
                continue
            if _losing(a - i, b - j):
                return 'WIN %d %d' % (i, j)
    return 'LOSE'
