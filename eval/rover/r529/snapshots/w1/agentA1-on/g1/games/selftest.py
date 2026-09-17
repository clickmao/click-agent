import subprocess, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(os.environ)
ENV.pop("PYTHONPATH", None)

CASES = [
    ("life", """11 5 4
#....
.....
...#.
.#.#.
.....
.#..#
.#...
###.#
#.#.#
..#..
....#""", """.....
.....
.....
.###.
.....
.....
..#..
.#.#.
...#.
..#..
....."""),
    ("life", """11 2 6
.#
##
..
##
.#
.#
..
#.
##
##
.#""", """##
##
..
##
##
..
..
..
..
..
.."""),
    ("life", "1 1 0\n#", "#"),
    ("life", "1 1 1\n#", "."),
    ("sub", "31 3\n1 6 10", "WIN 6"),
    ("sub", "19 1\n1", "WIN 1"),
    ("sub", "5 2\n1 3", "WIN 1"),
    ("sub", "6 2\n1 3", "LOSE"),
    ("nim", "3\n5 9 4", "WIN 2 8"),
    ("nim", "1\n3", "WIN 1 3"),
    ("nim", "2\n1 1", "LOSE"),
    ("nim", "4\n1 2 4 7", "LOSE"),
    ("wythoff", "21 25", "WIN 15 15"),
    ("wythoff", "10 9", "WIN 0 3"),
    ("wythoff", "1 2", "LOSE"),
    ("wythoff", "25 25", "WIN 25 25"),
]

fails = 0
for gid, inp, exp in CASES:
    p = subprocess.run([sys.executable, "-m", "games", gid],
                       input=inp, capture_output=True, text=True,
                       cwd=ROOT, env=ENV)
    ok = (p.stdout == exp) and p.returncode == 0 and p.stderr == ""
    if not ok:
        fails += 1
        print("FAIL", gid, "rc", p.returncode, "stderr", repr(p.stderr))
        print(" got", repr(p.stdout))
        print(" exp", repr(exp))
print("SELFTEST", "PASS" if fails == 0 else "FAIL",
      "cases", len(CASES), "fails", fails)
sys.exit(1 if fails else 0)
