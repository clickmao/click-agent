import subprocess
import sys

CASES = [
    ('life', 'tests/life1.txt', 'expected/life1.txt'),
    ('life', 'tests/life2.txt', 'expected/life2.txt'),
    ('sub', 'tests/sub1.txt', 'expected/sub1.txt'),
    ('sub', 'tests/sub2.txt', 'expected/sub2.txt'),
    ('nim', 'tests/nim1.txt', 'expected/nim1.txt'),
    ('nim', 'tests/nim2.txt', 'expected/nim2.txt'),
    ('wythoff', 'tests/wythoff1.txt', 'expected/wythoff1.txt'),
    ('wythoff', 'tests/wythoff2.txt', 'expected/wythoff2.txt'),
]

def norm(s):
    return s.rstrip('\n')

ok = True
for game, inp, exp in CASES:
    with open(inp) as f:
        data = f.read()
    with open(exp) as f:
        expected = f.read()
    p = subprocess.run([sys.executable, '-m', 'games', game], input=data,
                       capture_output=True, text=True)
    got = p.stdout
    if norm(got) != norm(expected):
        ok = False
        print('FAIL %s %s' % (game, inp))
        print('  expected: %r' % expected)
        print('  got:      %r' % got)
        print('  stderr:   %r' % p.stderr)
print('ALL PASS' if ok else 'SOME FAIL')
