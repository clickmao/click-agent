import subprocess
import sys


CASES = [
    ('life', 'tests/life1.txt', 'tests/expected_life1.txt'),
    ('life', 'tests/life2.txt', 'tests/expected_life2.txt'),
    ('sub', 'tests/sub1.txt', 'tests/expected_sub1.txt'),
    ('sub', 'tests/sub2.txt', 'tests/expected_sub2.txt'),
    ('nim', 'tests/nim1.txt', 'tests/expected_nim1.txt'),
    ('nim', 'tests/nim2.txt', 'tests/expected_nim2.txt'),
    ('wythoff', 'tests/wythoff1.txt', 'tests/expected_wythoff1.txt'),
    ('wythoff', 'tests/wythoff2.txt', 'tests/expected_wythoff2.txt'),
]


def norm(b):
    return b.decode('utf-8').rstrip()


def main():
    failures = 0
    for game, inp, exp in CASES:
        with open(inp, 'rb') as f:
            data = f.read()
        p = subprocess.run(
            [sys.executable, '-m', 'games', game],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        with open(exp, 'rb') as f:
            expected = f.read()
        ok = p.returncode == 0 and norm(p.stdout) == norm(expected) and norm(p.stderr) == ''
        print(game, inp, 'OK' if ok else 'FAIL')
        if not ok:
            failures += 1
            print('  rc=', p.returncode, 'stderr=', repr(p.stderr))
            print('  got=', repr(p.stdout))
            print('  exp=', repr(expected))
    print('TOTAL', len(CASES), 'FAILURES', failures)


if __name__ == '__main__':
    main()
