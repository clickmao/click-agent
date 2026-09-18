"""Multi-pile Nim: WIN with smallest pile and take count, or LOSE."""


def solve(text: str) -> str:
    lines = text.split('\n')
    if not lines or lines[0].strip() == '':
        return ''
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()][:m]
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN ' + str(idx + 1) + ' ' + str(a - target)
    return 'LOSE'
