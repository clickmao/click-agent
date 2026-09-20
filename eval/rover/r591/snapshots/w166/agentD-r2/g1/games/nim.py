def solve(text):
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    m = int(lines[0].split()[0])
    heaps = list(map(int, lines[1].split()))
    x = 0
    for a in heaps:
        x ^= a
    if x == 0:
        return 'LOSE'
    for i in range(m):
        target = heaps[i] ^ x
        if target < heaps[i]:
            return 'WIN %d %d' % (i + 1, heaps[i] - target)
    return 'LOSE'
