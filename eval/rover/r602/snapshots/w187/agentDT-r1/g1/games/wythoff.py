PHI = (1 + 5 ** 0.5) / 2


def _cold(x: int, y: int) -> bool:
    if x > y:
        x, y = y, x
    d = y - x
    return x == int(d * PHI)


def solve(text: str) -> str:
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    a, b = map(int, lines[idx].split())
    if _cold(a, b):
        return 'LOSE'
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if i != 0 and j != 0 and i != j:
                continue
            if _cold(a - i, b - j):
                return 'WIN ' + str(i) + ' ' + str(j)
    return 'LOSE'
