"""Multi-pile Nim: remove any positive number from a single pile.

Input text format:
    line 1: m (1..4)
    line 2: m pile sizes

solve(text) -> 'WIN p r' (p = smallest pile index, r = stones removed)
             or 'LOSE' when the XOR of all piles is zero.
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = []
    while idx < len(lines) and len(piles) < m:
        for tok in lines[idx].split():
            piles.append(int(tok))
        idx += 1
    piles = piles[:m]

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


if __name__ == '__main__':
    import sys
    sys.stdout.write(solve(sys.stdin.read()))
