from functools import lru_cache
import math, subprocess, json

# Verify losing set formula matches brute force
@lru_cache(None)
def win(a,b):
    if a==0 and b==0: return False
    for i in range(1,a+1):
        if not win(a-i,b): return True
    for j in range(1,b+1):
        if not win(a,b-j): return True
    for t in range(1,min(a,b)+1):
        if not win(a-t,b-t): return True
    return False

L=set()
for a in range(1000001):
    for b in range(1000001):
        if not win(a,b): L.add((a,b))

import games.wythoff as w
assert L == w._LOSING, (L ^ w._LOSING)
print("losing set OK", len(L))

# Verify solve matches brute force minimal lexicographic winning move
def brute(a,b):
    if not win(a,b): return "LOSE"
    for i in range(a+1):
        for j in range(b+1):
            if (i,j)==(0,0): continue
            if not ((i>0 and j==0) or (i==0 and j>0) or (i==j)): continue
            if not win(a-i,b-j):
                return "WIN %d %d"%(i,j)
for a in range(1000001):
    for b in range(1000001):
        exp=brute(a,b)
        got=w.solve(f"{a} {b}")
        assert exp==got, (a,b,exp,got)
print("all positions OK")
