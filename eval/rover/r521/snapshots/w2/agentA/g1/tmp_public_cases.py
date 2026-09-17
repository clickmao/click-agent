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

fails = 0
for gid, stdin, expected in CASES:
    p = subprocess.run([sys.executable, "-m", "games", gid], input=stdin,
                       capture_output=True, text=True)
    got = p.stdout[:-1] if p.stdout.endswith("\n") else p.stdout
    ok = (p.returncode == 0 and got == expected and p.stderr == "")
    if not ok:
        fails += 1
    print("%-8s rc=%d stderr=%r bytes_ok=%s" % (gid, p.returncode, p.stderr, got == expected))
print("FAILS", fails)
sys.exit(1 if fails else 0)
