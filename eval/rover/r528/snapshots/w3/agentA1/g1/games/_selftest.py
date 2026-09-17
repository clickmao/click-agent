import subprocess
import sys

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

fail = 0
for gid, inp, exp in CASES:
    p = subprocess.run([sys.executable, "-m", "games", gid], input=inp,
                       capture_output=True, text=True)
    got = p.stdout
    err = p.stderr
    ok = (got == exp) and (p.returncode == 0) and (err == "")
    if not ok:
        fail += 1
        print("FAIL", gid, "rc=%d" % p.returncode)
        print("  exp=%r" % exp)
        print("  got=%r" % got)
        print("  err=%r" % err)

# extra: life k=0 identity + stale-edge check
p = subprocess.run([sys.executable, "-m", "games", "life"],
                   input="1 1 0\n#\n", capture_output=True, text=True)
if p.stdout != "#":
    fail += 1
    print("FAIL life k=0 ident", repr(p.stdout))

print("PASS" if fail == 0 else "FAIL %d" % fail)
sys.exit(1 if fail else 0)
