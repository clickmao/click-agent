"""Standalone self-test, runnable directly with  python3 -I games/selftest.py .

It never relies on the package name being importable: the CLI is invoked in
file form (python3 -I games/<game_id>.py) so that `-I` (no cwd on sys.path)
does not break the check.  Any argv is accepted and ignored.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _run(game, inp):
    script = os.path.join(HERE, game + ".py")
    p = subprocess.run([sys.executable, "-I", script], input=inp,
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


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

NEG = [
    ("sub", "4 1\n1\n", "LOSE"),
    ("sub", "2 2\n1 3\n", "LOSE"),
    ("nim", "2\n3 3\n", "LOSE"),
    ("wythoff", "1 2\n", "LOSE"),
    ("wythoff", "2 1\n", "LOSE"),
    ("life", "1 1 5\n#\n", "."),
]


def main():
    n = 0
    bad = 0
    for cases in (CASES, NEG):
        for game, inp, exp in cases:
            n += 1
            rc, out, err = _run(game, inp)
            if rc == 0 and out == exp and err == "":
                print("PASS %s" % game)
            else:
                bad += 1
                print("FAIL %s rc=%d got=%r exp=%r err=%r"
                      % (game, rc, out, exp, err))
    print("PASS" if bad == 0 else "FAIL %d/%d" % (bad, n))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
