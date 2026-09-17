import subprocess, sys
from functools import lru_cache
import itertools

def run(gid, inp):
    p = subprocess.run([sys.executable, "-m", "games", gid], input=inp,
                       capture_output=True, text=True)
    assert p.returncode == 0, (gid, p.returncode, p.stderr)
    assert p.stderr == "", (gid, p.stderr)
    return p.stdout

inp1 = "11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n"
exp1 = ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."
inp2 = "11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n"
exp2 = "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."

cases = [
    ("life", inp1, exp1), ("life", inp2, exp2),
    ("sub", "31 3\n1 6 10\n", "WIN 6"), ("sub", "19 1\n1\n", "WIN 1"),
    ("nim", "3\n5 9 4\n", "WIN 2 8"), ("nim", "1\n3\n", "WIN 1 3"),
    ("wythoff", "21 25\n", "WIN 15 15"), ("wythoff", "10 9\n", "WIN 0 3"),
]
ok = True
for gid, inp, exp in cases:
    got = run(gid, inp)
    st = "PASS" if got == exp else "FAIL"
    if got != exp:
        ok = False
        print(st, gid, "\n  got=%r\n  exp=%r" % (got, exp))
    else:
        print(st, gid)

# --- life: independent simulation cross-check on random grids
import random
random.seed(1234)
def life_brute(H, W, k, grid):
    g = grid
    for _ in range(k):
        ng = [[0]*W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                n = 0
                for dr in (-1,0,1):
                    for dc in (-1,0,1):
                        if dr==0 and dc==0: continue
                        rr,cc=r+dr,c+dc
                        if 0<=rr<H and 0<=cc<W and g[rr][cc]: n+=1
                ng[r][c] = 1 if (n==3 or (g[r][c] and n==2)) else 0
        g = ng
    return "\n".join("".join('#' if x else '.' for x in row) for row in g)

for _ in range(40):
    H = random.randint(1, 8); W = random.randint(1, 8); k = random.randint(0, 6)
    grid = [[random.randint(0,1) for _ in range(W)] for _ in range(H)]
    txt = "%d %d %d\n" % (H, W, k) + "\n".join("".join('#' if x else '.' for x in row) for row in grid) + "\n"
    got = run("life", txt)
    exp = life_brute(H, W, k, grid)
    if got != exp:
        ok = False; print("FAIL life brute H,W,k=",H,W,k)

# --- sub: brute force all n<=80 against independent recursion
for n in range(1, 81):
    for moves in ([1], [1,6,10], list(range(1,13)), [1,3,4]):
        @lru_cache(None)
        def win(x):
            return any(not win(x-s) for s in moves if s <= x)
        txt = "%d %d\n%s\n" % (n, len(moves), " ".join(map(str, moves)))
        got = run("sub", txt)
        if win(n):
            m = min(s for s in moves if s <= n and not win(n-s))
            exp = "WIN %d" % m
        else:
            exp = "LOSE"
        if got != exp:
            ok = False; print("FAIL sub brute", n, moves, got, exp)

def nim_brute(piles):
    @lru_cache(None)
    def w(state):
        for i, a in enumerate(state):
            for t in range(1, a+1):
                ns = list(state); ns[i] -= t
                if not w(tuple(ns)):
                    return True
        return False
    return w(tuple(piles))

for m in (1,2,3,4):
    for piles in itertools.product(range(1,7), repeat=m):
        got = run("nim", "%d\n%s\n" % (m, " ".join(map(str, piles))))
        if nim_brute(piles):
            found = None
            for i, a in enumerate(piles):
                for t in range(1, a+1):
                    ns = list(piles); ns[i]-=t
                    if not nim_brute(tuple(ns)):
                        found = (i+1, t); break
                if found: break
            exp = "WIN %d %d" % found
        else:
            exp = "LOSE"
        if got != exp:
            ok = False; print("FAIL nim brute", piles, got, exp)

# --- wythoff: brute force all 1<=a,b<=25, independent game-tree + lexicographic move
@lru_cache(None)
def wyt_w(x, y):
    for i in range(1, x+1):
        if not wyt_w(x-i, y): return True
    for j in range(1, y+1):
        if not wyt_w(x, y-j): return True
    for t in range(1, min(x,y)+1):
        if not wyt_w(x-t, y-t): return True
    return False

def wyt_brute(a, b):
    if not wyt_w(a, b):
        return "LOSE"
    best = None
    for i in range(0, a+1):
        for j in range(0, b+1):
            if i==0 and j==0: continue
            if not wyt_w(a-i, b-j):
                if best is None or (i,j) < best:
                    best = (i,j)
    return "WIN %d %d" % best

for a in range(1, 26):
    for b in range(1, 26):
        got = run("wythoff", "%d %d\n" % (a, b))
        exp = wyt_brute(a, b)
        if got != exp:
            ok = False; print("FAIL wythoff brute", a, b, got, exp)

print("SELFTEST", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
