"""多堆 Nim: WIN p r / LOSE。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    idx += 1
    piles = [int(x) for x in lines[idx].split()][:m]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for pi in range(m):
        a = piles[pi]
        t = a ^ x
        if t < a:
            return 'WIN %d %d' % (pi + 1, a - t)
    return 'LOSE'
