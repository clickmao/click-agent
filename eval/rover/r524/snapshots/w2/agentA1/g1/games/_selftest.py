import subprocess, sys, os, math, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

def run(gid, inp):
    p = subprocess.run([sys.executable, "-m", "games", gid],
                       input=inp, capture_output=True, text=True, cwd=ROOT)
    assert p.stderr == "", "stderr not empty for %r: %r" % (inp, p.stderr)
    return p.stdout

fails = []
def check(name, got, want):
    if got != want:
        fails.append("%s: got %r want %r" % (name, got, want))

life1_in = "11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#"
life1_out = ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."
life2_in = "11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#"
life2_out = "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."
check("life1", run("life", life1_in), life1_out)
check("life2", run("life", life2_in), life2_out)
check("life_k0", run("life", "1 1 0\n#"), "#")

check("sub1", run("sub", "31 3\n1 6 10"), "WIN 6")
check("sub2", run("sub", "19 1\n1"), "WIN 1")

def sub_brute(n, moves):
    win = [False]*(n+1)
    for i in range(1, n+1):
        win[i] = any(i-s >= 0 and not win[i-s] for s in moves)
    if not win[n]: return "LOSE"
    for s in sorted(moves):
        if s <= n and not win[n-s]: return "WIN %d" % s
    return "LOSE"

random.seed(1)
for _ in range(200):
    n = random.randint(1, 80)
    k = random.randint(1, 12)
    extra = random.sample(range(2, 13), min(k-1, 11))
    moves = [1] + extra
    inp = "%d %d\n%s" % (n, len(moves), " ".join(map(str, moves)))
    check("sub-cross n=%d" % n, run("sub", inp), sub_brute(n, moves))

check("nim1", run("nim", "3\n5 9 4"), "WIN 2 8")
check("nim2", run("nim", "1\n3"), "WIN 1 3")

def nim_brute(piles):
    x = 0
    for a in piles: x ^= a
    if x == 0: return "LOSE"
    for i, a in enumerate(piles):
        t = a ^ x
        if t < a: return "WIN %d %d" % (i+1, a-t)
    return "LOSE"

for _ in range(200):
    m = random.randint(1, 4)
    piles = [random.randint(1, 15) for _ in range(m)]
    check("nim-cross", run("nim", "%d\n%s" % (m, " ".join(map(str, piles)))), nim_brute(piles))

check("wyth1", run("wythoff", "21 25"), "WIN 15 15")
check("wyth2", run("wythoff", "10 9"), "WIN 0 3")

N = 25
cold = [[False]*(N+1) for _ in range(N+1)]
for i in range(N+1):
    for j in range(N+1):
        if i == 0 and j == 0:
            cold[i][j] = True; continue
        ok = any(cold[x][j] for x in range(i)) or any(cold[i][y] for y in range(j))
        if not ok:
            for t in range(1, min(i, j)+1):
                if cold[i-t][j-t]: ok = True; break
        cold[i][j] = not ok

def wyth_brute(a, b):
    if cold[a][b]: return "LOSE"
    best = None
    for i in range(a+1):
        for j in range(b+1):
            if i == 0 and j == 0: continue
            if not (i == 0 or j == 0 or i == j): continue
            if cold[a-i][b-j]:
                c = (i, j)
                if best is None or c < best: best = c
    return "WIN %d %d" % best

bad = 0
for a in range(1, 26):
    for b in range(1, 26):
        try:
            got = run("wythoff", "%d %d" % (a, b))
        except AssertionError as e:
            bad += 1
            if len(fails) < 20: fails.append("wyth %d %d exc: %s" % (a, b, e))
            continue
        want = wyth_brute(a, b)
        if got != want:
            bad += 1
            if len(fails) < 20: fails.append("wyth %d %d: got %r want %r" % (a, b, got, want))
print("wythoff mismatches:", bad)

import games.life, games.sub, games.nim, games.wythoff  # noqa
assert games.sub.solve("19 1\n1") == "WIN 1"
assert not games.sub.solve("19 1\n1").endswith("\n")

if fails:
    print("FAIL")
    for f in fails[:20]: print(" ", f)
    sys.exit(1)
print("PASS")
sys.exit(0)
