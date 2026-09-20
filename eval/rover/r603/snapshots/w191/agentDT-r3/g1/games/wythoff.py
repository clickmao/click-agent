"""Wythoff game: losing-position test and lexicographically smallest winning move."""


def _is_losing(a: int, b: int) -> bool:
    if a > b:
        a, b = b, a
    for k in range(0, 30):
        p, q = int(k * (1 + 5 ** 0.5) / 2), int(k * (3 + 5 ** 0.5) / 2)
        if a == p and b == q:
            return True
        if p > a or q > b:
            return False
    return False


def solve(text: str) -> str:
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    a, b = map(int, lines[0].split())
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            # move must remove from a pile only, or same amount from both
            same_single = (j == 0 and 1 <= i <= a) or (i == 0 and 1 <= j <= b)
            same_both = (i == j and i >= 1)
            if not (same_single or same_both):
                continue
            if _is_losing(a - i, b - j):
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
