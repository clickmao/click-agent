import math
PHI = (1 + math.sqrt(5)) / 2
for n in range(0, 13):
    print(n, math.floor(n*PHI), math.floor(n*PHI*PHI), int((math.floor(n*PHI)-1)/PHI) if n else 0)
