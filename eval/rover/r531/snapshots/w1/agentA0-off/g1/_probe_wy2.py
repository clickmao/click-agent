N = 25
C = [[False] * (N + 1) for _ in range(N + 1)]
for t in range(0, 2 * N + 1):
    for a in range(0, min(t, N) + 1):
        b = t - a
        if b > N:
            continue
        w = any(C[a - i][b] for i in range(1, a + 1))
        if not w:
            w = any(C[a][b - j] for j in range(1, b + 1))
        if not w:
            w = any(C[a - k][b - k] for k in range(1, min(a, b) + 1))
        C[a][b] = not w
print("cold in 18..25:")
for a in range(18, 26):
    row = [b for b in range(18, 26) if C[a][b]]
    if row:
        print(a, row)
print("cold(15,25)", C[15][25])
