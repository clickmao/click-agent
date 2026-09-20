"""逐字节比对公开用例: python3 check.py。"""
import subprocess
import sys

CASES = [
    ('life', 'cases/life_1.txt'),
    ('life', 'cases/life_2.txt'),
    ('sub', 'cases/sub_1.txt'),
    ('sub', 'cases/sub_2.txt'),
    ('nim', 'cases/nim_1.txt'),
    ('nim', 'cases/nim_2.txt'),
    ('wythoff', 'cases/wythoff_1.txt'),
    ('wythoff', 'cases/wythoff_2.txt'),
]


def main() -> None:
    for game, path in CASES:
        with open(path) as f:
            data = f.read()
        with open(path.replace('.txt', '.expected.txt')) as f:
            expected = f.read()
        out = subprocess.run(
            [sys.executable, '-m', 'games', game],
            input=data, capture_output=True, text=True
        )
        got = out.stdout
        if got != expected:
            print('FAIL', game, path, repr(got), repr(expected))
            return
        if out.returncode != 0:
            print('RC', game, path, out.returncode)
            return
    print('ALL OK')


if __name__ == '__main__':
    main()
