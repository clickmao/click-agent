import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

CASES = [
    ('life', 'check_life1.txt',
     '11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n',
     '.....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n.....'),
    ('life', 'check_life2.txt',
     '11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n',
     '##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n..'),
    ('sub', 'check_sub1.txt', '31 3\n1 6 10\n', 'WIN 6'),
    ('sub', 'check_sub2.txt', '19 1\n1\n', 'WIN 1'),
    ('nim', 'check_nim1.txt', '3\n5 9 4\n', 'WIN 2 8'),
    ('nim', 'check_nim2.txt', '1\n3\n', 'WIN 1 3'),
    ('wythoff', 'check_wythoff1.txt', '21 25\n', 'WIN 15 15'),
    ('wythoff', 'check_wythoff2.txt', '10 9\n', 'WIN 0 3'),
]

ok = True
for game, path, inp, expected in CASES:
    p = subprocess.run(
        [sys.executable, '-m', 'games', game],
        input=inp, capture_output=True, text=True, cwd=ROOT, timeout=30)
    got = p.stdout
    if got.endswith('\n'):
        got = got[:-1]
    assert p.returncode == 0, (game, path, p.returncode, p.stderr)
    assert p.stderr == '', (game, path, repr(p.stderr))
    assert got == expected, (game, path, repr(got), repr(expected))

print('ALL OK')
