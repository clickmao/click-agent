"""公开用例逐字节校验: 调 python3 -m games <id> 比对期望文件。"""
import subprocess
import sys

CASES = [
    ('life', 'checks/run_life_1.txt', 'checks/exp_life_1.txt'),
    ('life', 'checks/run_life_2.txt', 'checks/exp_life_2.txt'),
    ('sub', 'checks/run_sub_1.txt', 'checks/exp_sub_1.txt'),
    ('sub', 'checks/run_sub_2.txt', 'checks/exp_sub_2.txt'),
    ('nim', 'checks/run_nim_1.txt', 'checks/exp_nim_1.txt'),
    ('nim', 'checks/run_nim_2.txt', 'checks/exp_nim_2.txt'),
    ('wythoff', 'checks/run_wythoff_1.txt', 'checks/exp_wythoff_1.txt'),
    ('wythoff', 'checks/run_wythoff_2.txt', 'checks/exp_wythoff_2.txt'),
]


def main() -> int:
    bad = 0
    for gid, infile, expfile in CASES:
        with open(infile, 'r') as f:
            data = f.read()
        with open(expfile, 'r') as f:
            exp = f.read()
        p = subprocess.run([sys.executable, '-m', 'games', gid],
                           input=data.encode(),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
        got = p.stdout.decode()
        if p.returncode != 0 or p.stderr or got != exp:
            bad += 1
            print('FAIL', gid, infile, repr(got[:80]), repr(p.stderr[:80]))
        else:
            print('OK', gid, infile)
    print('bad=' + str(bad))
    return 0


if __name__ == '__main__':
    sys.exit(main())
