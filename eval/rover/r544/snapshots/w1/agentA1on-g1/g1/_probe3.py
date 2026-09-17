import games.wythoff as w

for a, b in [(1, 2), (1, 3), (0, 0), (0, 1), (2, 2)]:
    print(a, b, w._is_cold(a, b))
print("phi**2 approx:", 1.618033988749895 ** 2)
for n in range(1, 6):
    phi = 1.618033988749895
    print(n, int(n * phi), int(n * phi * phi), int(n * phi) + n)
