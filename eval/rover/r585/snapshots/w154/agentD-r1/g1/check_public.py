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

ok = True
for game_id, inp, exp in CASES:
    r = subprocess.run([sys.executable, "-m", "games", game_id],
                       input=inp, capture_output=True, text=True)
    got = r.stdout
    if got != exp:
        ok = False
        sys.stderr.write("FAIL %s: got=%r exp=%r\n" % (game_id, got, exp))
    if r.stderr:
        ok = False
        sys.stderr.write("STDERR non-empty for %s: %r\n" % (game_id, r.stderr))
    if r.returncode != 0:
        ok = False
        sys.stderr.write("RC != 0 for %s\n" % game_id)

if ok:
    sys.stdout.write("ALL_PUBLIC_OK\n")
else:
    sys.stdout.write("FAILED\n")
