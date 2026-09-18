import subprocess, sys

CASES = [
    ("life", "11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n",
     ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."),
    ("life", "11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n",
     "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."),
    ("sub", "31 3\n1 6 10\n", "WIN 6"),
    ("sub", "19 1\n1\n", "WIN 1"),
    ("nim", "3\n5 9 4\n", "WIN 2 8"),
    ("nim", "1\n3\n", "WIN 1 3"),
    ("wythoff", "21 25\n", "WIN 15 15"),
    ("wythoff", "10 9\n", "WIN 0 3"),
]

# Extra: Wythoff cold positions (P-positions) must be LOSE.
COLD = [(1, 2), (3, 5), (4, 7), (2, 1), (5, 3)]
# Extra: life k=0 returns input unchanged.
EXTRA_LIFE = [("3 3 0\n.#.\n.#.\n.#.\n", ".#.\n.#.\n.#.")]
# Extra: nim xor==0 -> LOSE.
EXTRA_NIM = [("2\n3 3\n", "LOSE")]
# Extra: sub total = 0 mod something -> from spec: n=1,k=1,s=1 -> WIN 1
EXTRA_SUB = [("1 1\n1\n", "WIN 1"), ("2 2\n1 2\n", "LOSE")]

bad = 0
def run(gid, inp):
    p = subprocess.run([sys.executable, "-m", "games", gid], input=inp,
                       capture_output=True, text=True)
    return p

for gid, inp, exp in CASES:
    p = run(gid, inp)
    if not (p.returncode == 0 and p.stdout == exp and p.stderr == ""):
        bad += 1
        print("FAIL", gid, "got", repr(p.stdout), "exp", repr(exp), "stderr", repr(p.stderr))

for inp, exp in EXTRA_LIFE:
    p = run("life", inp)
    if p.stdout != exp: bad += 1; print("FAIL life-extra", repr(p.stdout))
for inp, exp in EXTRA_NIM:
    p = run("nim", inp)
    if p.stdout != exp: bad += 1; print("FAIL nim-extra", repr(p.stdout))
for inp, exp in EXTRA_SUB:
    p = run("sub", inp)
    if p.stdout != exp: bad += 1; print("FAIL sub-extra", repr(p.stdout))
for a, b in COLD:
    p = run("wythoff", "%d %d\n" % (a, b))
    if p.stdout != "LOSE": bad += 1; print("FAIL wythoff-cold", a, b, repr(p.stdout))

print("cases", len(CASES)+len(EXTRA_LIFE)+len(EXTRA_NIM)+len(EXTRA_SUB)+len(COLD), "fail", bad)
sys.exit(1 if bad else 0)
