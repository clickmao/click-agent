from functools import reduce


def solve(text: str) -> str:
    lines = text.split('\n')
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()[:m]]
    x = reduce(lambda a, b: a ^ b, piles, 0)
    if x == 0:
        return 'LOSE'
    for i, a in enumerate(piles):
        target = a ^ x
        if target < a:
            return 'WIN ' + str(i + 1) + ' ' + str(a - target)
    return 'LOSE'
