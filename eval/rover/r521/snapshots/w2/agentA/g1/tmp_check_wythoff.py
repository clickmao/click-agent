import sys
sys.path.insert(0, '.')
from games import wythoff

N = 26
cold = {}
for a in range(N + 1):
    for b in range(N + 1):
        if a == 0 and b == 0:
            cold[(a, b)] = True
            continue
        win = False
        for i in range(0, a + 1):
            for j in range(0, b + 1):
                if i == 0 and j == 0:
                    continue
                if i == 0 or j == 0 or i == j:
                    if cold[(a - i, b - j)]:
                        win = True
                        break
            if win:
                break
        cold[(a, b)] = not win

# candidate exact cold check (current implementation)
mism = [(a, b) for a in range(1, 26) for b in range(1, 26)
        if wythoff._is_cold(a, b) != cold[(a, b)]]
print('current _is_cold mismatches:', len(mism), mism[:5])

errs = []
for a in range(1, 26):
    for b in range(1, 26):
        out = wythoff.solve('%d %d' % (a, b))
        if cold[(a, b)]:
            if out != 'LOSE':
                errs.append((a, b, 'expected LOSE', out))
        else:
            if not out.startswith('WIN '):
                errs.append((a, b, 'expected WIN', out))
                continue
            i, j = map(int, out.split()[1:])
            legal = i <= a and j <= b and (i == 0 or j == 0 or i == j) and not (i == 0 and j == 0)
            if not legal or not cold[(a - i, b - j)]:
                errs.append((a, b, 'illegal/not winning', out))
print('current solve errors:', len(errs), errs[:5])
