import subprocess, sys, random

def run(gid, inp):
    p = subprocess.run([sys.executable, "-m", "games", gid],
                       input=inp, capture_output=True, text=True)
    assert p.returncode == 0, (gid, p.returncode, p.stderr)
    assert p.stderr == "", (gid, p.stderr)
    return p.stdout

cases = [
 ("life", "11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#", ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."),
 ("life", "11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#", "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."),
 ("sub", "31 3\n1 6 10", "WIN 6"),
 ("sub", "19 1\n1", "WIN 1"),
 ("nim", "3\n5 9 4", "WIN 2 8"),
 ("nim", "1\n3", "WIN 1 3"),
 ("wythoff", "21 25", "WIN 15 15"),
 ("wythoff", "10 9", "WIN 3 0"),
]
bad = 0
for gid, inp, exp in cases:
    got = run(gid, inp)
    ok = got == exp
    bad += not ok
    print(gid, "OK" if ok else "FAIL")
    if not ok:
        print(" exp:", repr(exp)); print(" got:", repr(got))

g = "2 3 0\n.#.\n###"
assert run("life", g) == ".#.\n###", "life k=0"
print("life k=0 OK")

def brute_sub(n, steps):
    win = [False]*(n+1)
    for i in range(1, n+1):
        win[i] = any(not win[i-s] for s in steps if s <= i)
    if not win[n]:
        return "LOSE"
    for s in sorted(steps):
        if s <= n and not win[n-s]:
            return f"WIN {s}"

random.seed(1)
for _ in range(200):
    n = random.randint(1, 80); k = random.randint(1, 12)
    pool = list(range(2, 13)); random.shuffle(pool)
    steps = set([1] + pool[:k-1])
    inp = f"{n} {len(steps)}\n{' '.join(map(str, sorted(steps)))}"
    assert run("sub", inp) == brute_sub(n, steps), ("sub", inp)
print("sub brute OK")

def brute_nim(piles):
    x = 0
    for a in piles:
        x ^= a
    if x == 0:
        return "LOSE"
    for i, a in enumerate(piles, 1):
        t = a ^ x
        if t < a:
            return f"WIN {i} {a-t}"

for _ in range(200):
    m = random.randint(1, 4); piles = [random.randint(1, 15) for _ in range(m)]
    inp = f"{m}\n{' '.join(map(str, piles))}"
    assert run("nim", inp) == brute_nim(piles), ("nim", inp)
print("nim brute OK")

from functools import lru_cache
@lru_cache(maxsize=None)
def wlo(a, b):
    if a > b:
        a, b = b, a
    if a == 0 and b == 0:
        return True
    for i in range(1, a+1):
        if not wlo(a-i, b):
            return False
    for j in range(1, b+1):
        if not wlo(a, b-j):
            return False
    for t in range(1, min(a, b)+1):
        if not wlo(a-t, b-t):
            return False
    return True

bad_w = 0
for a in range(1, 26):
    for b in range(1, 26):
        got = run("wythoff", f"{a} {b}")
        if wlo(a, b):
            exp = "LOSE"
        else:
            # reference orientation: first pile = input a, second = input b
            best = None
            for i in range(a+1):
                for j in range(b+1):
                    if i == 0 and j == 0:
                        continue
                    if i and j and i != j:
                        continue
                    if not wlo(a-i, b-j):
                        if best is None or (i, j) < best:
                            best = (i, j)
            exp = f"WIN {best[0]} {best[1]}"
        if got != exp:
            bad_w += 1
            if bad_w <= 5:
                print("WYTHOFF MISMATCH", a, b, "got", got, "exp", exp)
print("wythoff mismatches:", bad_w)
print("ALL PASS" if bad == 0 and bad_w == 0 else "FAILURES", bad, bad_w)
