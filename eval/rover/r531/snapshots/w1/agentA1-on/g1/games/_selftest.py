"""Self-test: run `python3 -m games._selftest`, prints PASS/FAIL, exit 0 on pass."""

import subprocess
import sys

LIFE1 = "11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n"
LIFE1_EXP = ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."
LIFE2 = "11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n"
LIFE2_EXP = "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."

CASES = [
    ("life", "11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n", LIFE1_EXP),
    ("life", LIFE2, LIFE2_EXP),
    ("sub", "31 3\n1 6 10\n", "WIN 6"),
    ("sub", "19 1\n1\n", "WIN 1"),
    ("nim", "3\n5 9 4\n", "WIN 2 8"),
    ("nim", "1\n3\n", "WIN 1 3"),
    ("wythoff", "21 25\n", "WIN 15 15"),
    ("wythoff", "10 9\n", "WIN 0 3"),
]


def _run(game, stdin_text):
    p = subprocess.run(
        [sys.executable, "-m", "games", game],
        input=stdin_text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.returncode, p.stdout.decode("utf-8"), p.stderr.decode("utf-8")


def main() -> int:
    ok = True
    for game, stdin_text, expected in CASES:
        rc, out, err = _run(game, stdin_text)
        good = (rc == 0 and out == expected and err == "")
        ok = ok and good
        print("{} {} rc={} err={!r}".format("PASS" if good else "FAIL", game, rc, err))
        if not good:
            print("  got={!r}\n  exp={!r}".format(out, expected))
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
