"""多堆 Nim：堆号最小的必胜着法。"""


def solve(text: str) -> str:
    lines = text.split()
    m = int(lines[0])
    a = [int(x) for x in lines[1:1 + m]]
    xor = 0
    for v in a:
        xor ^= v
    if xor == 0:
        return 'LOSE'
    for i in range(m):
        target = a[i] ^ xor
        if target < a[i]:
            return 'WIN ' + str(i + 1) + ' ' + str(a[i] - target)
    return 'LOSE'
