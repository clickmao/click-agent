"""Byte-compare public cases against the modules' solve()."""

import subprocess
import sys

CASES = {
    'life': [
        ("11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n",
         ".....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n....."),
        ("11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n",
         "##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n.."),
    ],
    'sub': [
        ("31 3\n1 6 10\n", "WIN 6"),
        ("19 1\n1\n", "WIN 1"),
    ],
    'nim': [
        ("3\n5 9 4\n", "WIN 2 8"),
        ("1\n3\n", "WIN 1 3"),
    ],
    'wythoff': [
        ("21 25\n", "WIN 15 15"),
        ("10 9\n", "WIN 0 3"),
    ],
}


def main():
    ok = True
    for game, cases in CASES.items():
        for idx, (stdin_text, expected) in enumerate(cases):
            proc = subprocess.run(
                [sys.executable, '-m', 'games', game],
                input=stdin_text, capture_output=True, text=True,
            )
            got = proc.stdout.rstrip('\n')
            if proc.returncode != 0 or got != expected or proc.stderr != '':
                ok = False
                print('FAIL', game, idx, repr(got), repr(proc.stderr), proc.returncode)
            else:
                print('PASS', game, idx)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
