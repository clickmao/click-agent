import importlib
import io
import sys

CASES = [
    ('life', 't_life1.txt', 'e_life1.txt'),
    ('life', 't_life2.txt', 'e_life2.txt'),
    ('sub', 't_sub1.txt', 'e_sub1.txt'),
    ('sub', 't_sub2.txt', 'e_sub2.txt'),
    ('nim', 't_nim1.txt', 'e_nim1.txt'),
    ('nim', 't_nim2.txt', 'e_nim2.txt'),
    ('wythoff', 't_wy1.txt', 'e_wy1.txt'),
    ('wythoff', 't_wy2.txt', 'e_wy2.txt'),
]
MODS = {}
for name in ('life', 'sub', 'nim', 'wythoff'):
    MODS[name] = importlib.import_module('games.' + name)

ok = True
for game, inp, exp in CASES:
    with open(inp, 'r') as f:
        text = f.read()
    with open(exp, 'r') as f:
        want = f.read()
    got = MODS[game].solve(text)
    if got.rstrip('\n') != want.rstrip('\n'):
        sys.stderr.write('FAIL %s %s\n' % (game, inp))
        ok = False

buf = io.StringIO()
sys.stdin = io.StringIO('3\n5 9 4\n')
sys.stdout = buf
import runpy
runpy.run_module('games', run_name='__main__')
sys.stdout = sys.__stdout__
if buf.getvalue().rstrip('\n') != 'WIN 2 8':
    sys.stderr.write('FAIL CLI nim\n')
    ok = False

sys.stderr.write('')
print('ALL OK' if ok else 'ALL NG')
