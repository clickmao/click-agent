import runpy
import sys


def run(mod, inp):
    old_in, old_out = sys.stdin, sys.stdout
    sys.stdin = type('S', (), {'read': staticmethod(lambda: inp)})()
    buf = []
    sys.stdout = type('O', (), {'write': staticmethod(buf.append)})()
    try:
        ns = runpy.run_module('games.' + mod, run_name='__main__')
    except SystemExit as e:
        if e.code not in (None, 0):
            raise
    finally:
        sys.stdin, sys.stdout = old_in, old_out
    return ''.join(buf)


cases = [
    ('life', open('check_life_1.txt').read(), open('check_life_1.exp').read()),
    ('life', open('check_life_2.txt').read(), open('check_life_2.exp').read()),
    ('sub', open('check_sub_1.txt').read(), open('check_sub_1.exp').read()),
    ('sub', open('check_sub_2.txt').read(), open('check_sub_2.exp').read()),
    ('nim', open('check_nim_1.txt').read(), open('check_nim_1.exp').read()),
    ('nim', open('check_nim_2.txt').read(), open('check_nim_2.exp').read()),
    ('wythoff', open('check_wythoff_1.txt').read(), open('check_wythoff_1.exp').read()),
    ('wythoff', open('check_wythoff_2.txt').read(), open('check_wythoff_2.exp').read()),
]

for mod, inp, exp in cases:
    got = run(mod, inp)
    assert got == exp, (mod, repr(got), repr(exp))
print('ALL_PASS')
