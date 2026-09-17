import math
phi = (1 + math.sqrt(5)) / 2

def cold(x, y):
    if x > y:
        x, y = y, x
    if x == 0 and y == 0:
        return True
    n = round((y - x) / phi)
    if n <= 0:
        return False
    return math.floor(n * phi) == x and math.floor(n * phi * phi) == y

a, b = 21, 25
print("a,b cold?", cold(a, b))
found = []
for i in range(0, a + 1):
    for j in range(0, b + 1):
        if i == 0 and j == 0:
            continue
        if i > 0 and j > 0 and i != j:
            continue
        if cold(a - i, b - j):
            found.append((i, j))
print("moves:", found[:10])
# enumerate reachable square-cold positions independent of iphi test
print("cold tab:", [(x, y) for x in range(0, 26) for y in range(x, 26) if cold(x, y)])
