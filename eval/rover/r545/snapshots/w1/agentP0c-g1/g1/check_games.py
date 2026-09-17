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

bad = 0
for gid, inp, exp in CASES:
    r = subprocess.run([sys.executable, '-m', 'games', gid], input=inp,
                       capture_output=True, text=True)
    got = r.stdout
    ok = (got == exp)
    if not ok:
        bad += 1
        print('FAIL %s %r expected %r rc %d stderr %r' % (gid, got, exp, r.returncode, r.stderr))
print('ALL_OK' if bad == 0 else 'SOME_FAIL')
