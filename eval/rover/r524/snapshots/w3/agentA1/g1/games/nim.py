"""Nim: decide winner and the canonical winning move.

Input format:
    m               (1 <= m <= 4 piles)
    a1..am          (1 <= ai <= 15 stones per pile)

Players alternately remove any positive number of stones from exactly one
pile; whoever takes the last stone wins.  Output for a first-player win:
    WIN p r         p = smallest pile index (1-based) with a winning move,
                    r = number of stones removed from that pile
Otherwise:
    LOSE
"""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return ''
    m = int(lines[0])
    piles = [int(x) for x in lines[1].split()][:m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'

    # Find the smallest-index pile whose current size has the winning
    # target size below it (target = a ^ x < a is necessary and sufficient).
    for i in range(m):
        a = piles[i]
        target = a ^ x
        if target < a:
            return 'WIN {} {}'.format(i + 1, a - target)
    return 'LOSE'
