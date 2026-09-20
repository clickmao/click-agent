"""Multi-pile Nim: smallest pile index winning move.

Input layout (whole stdin text):
    m
    a1 a2 ... am
Output: 'WIN p r' (p 1-based pile index, r stones taken) or 'LOSE',
no trailing newline. Lose iff xor of all piles is 0.
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    if not lines or not lines[0].strip():
        return ''
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN %d %d' % (i + 1, a - target)
    return 'LOSE'
