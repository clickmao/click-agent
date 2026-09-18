"""Multi-pile Nim: WIN p r with smallest heap index, else LOSE."""


def solve(text):
    lines = text.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    m = int(lines[0].split()[0])
    heaps = [int(x) for x in lines[1].split()]
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        a = heaps[idx]
        target = a ^ x
        if target < a:
            return 'WIN ' + str(idx + 1) + ' ' + str(a - target)
    return 'LOSE'
