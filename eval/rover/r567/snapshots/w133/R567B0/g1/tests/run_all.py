"""公开用例逐字节比对：对四款游戏分别调用 games.<mod>.solve 与期望文件比较。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from games import life, nim, sub, wythoff

HERE = os.path.dirname(os.path.abspath(__file__))

MODS = {
    'life': life,
    'sub': sub,
    'nim': nim,
    'wythoff': wythoff,
}

PAIRS = [
    ('life', 'case_life1.txt', 'exp_life1.txt'),
    ('life', 'case_life2.txt', 'exp_life2.txt'),
    ('sub', 'case_sub1.txt', 'exp_sub1.txt'),
    ('sub', 'case_sub2.txt', 'exp_sub2.txt'),
    ('nim', 'case_nim1.txt', 'exp_nim1.txt'),
    ('nim', 'case_nim2.txt', 'exp_nim2.txt'),
    ('wythoff', 'case_wythoff1.txt', 'exp_wythoff1.txt'),
    ('wythoff', 'case_wythoff2.txt', 'exp_wythoff2.txt'),
]


def main():
    ok = True
    for game, cin, cexp in PAIRS:
        with open(os.path.join(HERE, cin), 'r', encoding='utf-8') as f:
            data = f.read()
        with open(os.path.join(HERE, cexp), 'r', encoding='utf-8') as f:
            exp = f.read()
        got = MODS[game].solve(data)
        if got != exp:
            ok = False
            print('MISMATCH %s %s' % (game, cin))
            print('--- got ---')
            print(repr(got))
            print('--- exp ---')
            print(repr(exp))
    if ok:
        print('ALL OK')


if __name__ == '__main__':
    main()
