import games.wythoff as w
print(sorted(w._COLD))
phi = (1.0 + 5.0 ** 0.5) / 2.0
for n in range(1, 6):
    p = int(n * phi)
    print(n, p, p + n)
print("(1,1) cold?", w._is_cold(1, 1))
print("(0,0) cold?", w._is_cold(0, 0))
