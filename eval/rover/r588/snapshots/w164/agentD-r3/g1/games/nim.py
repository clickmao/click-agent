def solve(text):
    lines = text.split('\n')
    idx = 0
    while idx < len(lines) and lines[idx].strip() == '':
        idx += 1
    m = int(lines[idx].split()[0])
    heaps = list(map(int, lines[idx + 1].split()))
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return 'LOSE'
    for p in range(m):
        target = heaps[p] ^ x
        if target < heaps[p]:
            return 'WIN ' + str(p + 1) + ' ' + str(heaps[p] - target)
    return 'LOSE'
