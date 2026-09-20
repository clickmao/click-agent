"""Byte-compare stdout of `python3 -m games <game>` against expected files."""
import subprocess
import sys

CASES = [
    ('life', 'public/life1.in', 'public/life1.out'),
    ('sub', 'public/sub1.in', 'public/sub1.out'),
    ('nim', 'public/nim1.in', 'public/nim1.out'),
    ('wythoff', 'public/wythoff1.in', 'public/wythoff1.out'),
]


def main() -> int:
    ok = True
    for game_id, inp, exp in CASES:
        with open(inp, 'rb') as f:
            data = f.read()
        res = subprocess.run(
            [sys.executable, '-m', 'games', game_id],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        with open(exp, 'rb') as f:
            want = f.read()
        got = res.stdout
        if res.returncode != 0 or got != want or res.stderr != b'':
            ok = False
            print('FAIL', game_id, 'rc=', res.returncode)
            print('  want=', want)
            print('  got =', got)
            print('  err =', res.stderr)
    if ok:
        print('ALL OK')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
