"""逐字节比对题目公开用例（stdout）。"""
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

fails = []
for gid, inp, exp in CASES:
    p = subprocess.run([sys.executable, '-m', 'games', gid], input=inp,
                       capture_output=True, text=True)
    if p.returncode != 0 or p.stdout != exp:
        fails.append((gid, p.returncode, p.stdout, exp))
        print('FAIL', gid, repr(p.stdout), 'expected', repr(exp))
print('SUMMARY ok=%d fail=%d' % (len(CASES) - len(fails), len(fails)))
sys.exit(1 if fails else 0)
