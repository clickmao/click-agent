"""Headless self-test for the games package.  Run from the workspace root:

    python3 -m games._selftest

Prints PASS/FAIL per case; exit code 0 iff all pass.
"""

from __future__ import annotations

import sys

from games import life, nim, sub, wythoff

CASES = [
    ('life', '11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#',
     '.....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n.....'),
    ('life', '11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#',
     '##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n..'),
    ('life', '1 1 0\n#', '#'),
    ('sub', '31 3\n1 6 10', 'WIN 6'),
    ('sub', '19 1\n1', 'WIN 1'),
    ('sub', '1 1\n1', 'WIN 1'),
    ('nim', '3\n5 9 4', 'WIN 2 8'),
    ('nim', '1\n3', 'WIN 1 3'),
    ('nim', '2\n1 1', 'LOSE'),
    ('wythoff', '21 25', 'WIN 15 15'),
    ('wythoff', '10 9', 'WIN 0 3'),
    ('wythoff', '1 2', 'LOSE'),
    ('wythoff', '2 1', 'LOSE'),
]

_SOLVERS = {'life': life.solve, 'sub': sub.solve, 'nim': nim.solve,
            'wythoff': wythoff.solve}


def main() -> int:
    fails = 0
    for game, text, expected in CASES:
        got = _SOLVERS[game](text)
        ok = got == expected
        if not ok:
            fails += 1
            sys.stdout.write('FAIL %s\n  in=%r\n  exp=%r\n  got=%r\n'
                             % (game, text, expected, got))
    sys.stdout.write('PASS %d/%d\n' % (len(CASES) - fails, len(CASES)))
    return 0 if fails == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
