"""Replay the 8 public cases through `python3 -m games <game_id>` and report diffs."""

import subprocess
import sys

CASES = [
    ('life', '11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n',
     '.....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n.....\n'),
    ('life', '11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n',
     '##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n..\n'),
    ('sub', '31 3\n1 6 10\n', 'WIN 6\n'),
    ('sub', '19 1\n1\n', 'WIN 1\n'),
    ('nim', '3\n5 9 4\n', 'WIN 2 8\n'),
    ('nim', '1\n3\n', 'WIN 1 3\n'),
    ('wythoff', '21 25\n', 'WIN 15 15\n'),
    ('wythoff', '10 9\n', 'WIN 0 3\n'),
]

fails = 0
for game, stdin, want in CASES:
    p = subprocess.run([sys.executable, '-m', 'games', game], input=stdin,
                       capture_output=True, text=True)
    got = p.stdout
    ok = got.rstrip('\n') == want.rstrip('\n') and p.stderr == ''
    if not ok:
        fails += 1
        print('FAIL %s stdin=%r' % (game, stdin))
        print('want=%r' % want.rstrip('\n'))
        print('got =%r' % got.rstrip('\n'))
        print('err =%r' % p.stderr)
sys.exit(1 if fails else 0)
