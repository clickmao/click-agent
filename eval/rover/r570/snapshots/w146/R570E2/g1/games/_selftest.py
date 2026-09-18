"""Public-case regression runner (stdlib only)."""
import subprocess
import sys

LIFE_INPUT = """11 5 4
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
....#
"""
LIFE_EXPECT = """.....
.....
.....
.###.
.....
.....
..#..
.#.#.
...#.
..#..
....."""

LIFE_INPUT2 = """11 2 6
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
.#
"""
LIFE_EXPECT2 = """##
##
..
##
##
..
..
..
..
..
.."""

SUB_INPUT = "31 3\n1 6 10\n"
SUB_EXPECT = "WIN 6"
SUB_INPUT2 = "19 1\n1\n"
SUB_EXPECT2 = "WIN 1"

NIM_INPUT = "3\n5 9 4\n"
NIM_EXPECT = "WIN 2 8"
NIM_INPUT2 = "1\n3\n"
NIM_EXPECT2 = "WIN 1 3"

WYTH_INPUT = "21 25\n"
WYTH_EXPECT = "WIN 15 15"
WYTH_INPUT2 = "10 9\n"
WYTH_EXPECT2 = "WIN 0 3"

CASES = [
    ("life", LIFE_INPUT, LIFE_EXPECT),
    ("life", LIFE_INPUT2, LIFE_EXPECT2),
    ("sub", SUB_INPUT, SUB_EXPECT),
    ("sub", SUB_INPUT2, SUB_EXPECT2),
    ("nim", NIM_INPUT, NIM_EXPECT),
    ("nim", NIM_INPUT2, NIM_EXPECT2),
    ("wythoff", WYTH_INPUT, WYTH_EXPECT),
    ("wythoff", WYTH_INPUT2, WYTH_EXPECT2),
]


GOOD = [
    # life: k=0 returns the initial grid verbatim
    ("life", "1 1 0\n#\n", "#"),
    # life: single dead cell stays dead; single live cell dies
    ("life", "1 1 1\n.\n", "."),
    ("life", "1 1 1\n#\n", "."),
    # sub: n=1 with s={1} is a win by taking 1
    ("sub", "1 1\n1\n", "WIN 1"),
    # sub: smallest winning move wins over larger ones
    ("sub", "2 2\n2 1\n", "WIN 1"),
    # nim: standard losing position
    ("nim", "2\n1 1\n", "LOSE"),
    # wythoff: (1,2) is a classic losing (cold) position
    ("wythoff", "1 2\n", "LOSE"),
    # wythoff: (2,1) same cold position, order-insensitive
    ("wythoff", "2 1\n", "LOSE"),
]


def run(game_id, text):
    proc = subprocess.run(
        [sys.executable, "-m", "games", game_id],
        input=text,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def check(label, game_id, text, expected):
    rc, out, err = run(game_id, text)
    if rc != 0:
        print("FAIL", label, "rc", rc, "stderr", err.strip())
        return False
    if out.rstrip() != expected.rstrip():
        print("FAIL", label, "got", repr(out), "want", repr(expected))
        return False
    return True


ok = 0
for game_id, text, expected in CASES:
    if check("public:" + game_id, game_id, text, expected):
        ok += 1
public_ok = ok

for game_id, text, expected in GOOD:
    if check("self:" + game_id, game_id, text, expected):
        ok += 1

print(str(public_ok) + " " + str(len(GOOD)) + " " + str(ok))
