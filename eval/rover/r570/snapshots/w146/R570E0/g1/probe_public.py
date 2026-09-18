import subprocess
import sys

CASES = [
    ('life', '11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n', '.....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n.....'),
    ('life', '11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n', '##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n..'),
    ('sub', '31 3\n1 6 10\n', 'WIN 6'),
    ('sub', '19 1\n1\n', 'WIN 1'),
    ('nim', '3\n5 9 4\n', 'WIN 2 8'),
    ('nim', '1\n3\n', 'WIN 1 3'),
    ('wythoff', '21 25\n', 'WIN 15 15'),
    ('wythoff', '10 9\n', 'WIN 0 3'),
]

ok = True
for idx, (game, inp, exp) in enumerate(CASES):
    p = subprocess.run([sys.executable, '-m', 'games', game], input=inp,
                       capture_output=True, text=True)
    got = p.stdout
    if p.returncode != 0 or got != exp:
        ok = False
        print('case %d %s FAIL' % (idx, game))
        print('rc=%s' % p.returncode)
        print('stdout=%r' % got)
        print('stderr=%r' % p.stderr)
    else:
        print('case %d %s OK' % (idx, game))
if not ok:
    sys.exit(1)
