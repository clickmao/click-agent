"""Enumerate all legal moves from (21,25) and test each against brute DP."""
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

a, b = 21, 25
wins = []
for i in range(a + 1):
    for j in range(b + 1):
        if i == 0 and j == 0:
            continue
        if C[a - i][b - j]:
            wins.append((i, j))
print("all winning moves from (21,25):", wins)
print("lex smallest:", wins[0] if wins else None)
