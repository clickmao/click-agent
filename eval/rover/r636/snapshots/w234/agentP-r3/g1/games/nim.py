"""多堆 Nim: 返回 "WIN p r" 或 "LOSE"。"""


def solve(text: str) -> str:
    lines = text.split('\n')
    if lines and lines[-1].strip() == '':
        lines.pop()
    m = int(lines[0].split()[0])
    piles = [int(x) for x in lines[1].split()]

    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return 'LOSE'
    for idx in range(m):
        target = piles[idx] ^ x
        if target < piles[idx]:
            return 'WIN %d %d' % (idx + 1, piles[idx] - target)
    return 'LOSE'
