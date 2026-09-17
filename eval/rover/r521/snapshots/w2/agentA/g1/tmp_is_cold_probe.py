import sys
sys.path.insert(0, '.')

# inspect the two candidate implementations of _is_cold
def is_cold_cur(a, b):
    if a > b:
        a, b = b, a
    n = int((b - a) * 0.6180339887498949)
    for cand in (n - 1, n, n + 1):
        if cand >= 0:
            x = (cand * 6180339887498949) // 10000000000000000
            if (x, x + cand) == (a, b):
                return True
    return False

def is_cold_fix(a, b):
    if a > b:
        a, b = b, a
    n = int(b - a)
    x = (n * 6180339887498949) // 10000000000000000
    y = x + n
    return (x, y) == (a, b)

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

bad_cur = [(a, b) for a in range(1, 26) for b in range(1, 26) if is_cold_cur(a, b) != cold[(a, b)]]
bad_fix = [(a, b) for a in range(1, 26) for b in range(1, 26) if is_cold_fix(a, b) != cold[(a, b)]]
print('cur mismatches:', len(bad_cur), bad_cur[:5])
print('fix mismatches:', len(bad_fix), bad_fix[:5])
# print the true cold table for range to eyeball
true_cold = sorted(k for k, v in cold.items() if v and k[0] > 0 and k[1] > 0)
print('true cold positions:', true_cold)
