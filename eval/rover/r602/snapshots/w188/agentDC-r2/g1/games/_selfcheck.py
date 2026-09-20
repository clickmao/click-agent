"""仅本地自检: 逐字节比对题面公开用例 (不参与评分, 无副作用)。

用法: python3 -m games._selfcheck
"""

from . import life
from . import nim
from . import sub
from . import wythoff

CASES = [
    (life, '11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#\n',
     '.....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n.....'),
    (life, '11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#\n',
     '##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n..'),
    (sub, '31 3\n1 6 10\n', 'WIN 6'),
    (sub, '19 1\n1\n', 'WIN 1'),
    (nim, '3\n5 9 4\n', 'WIN 2 8'),
    (nim, '1\n3\n', 'WIN 1 3'),
    (wythoff, '21 25\n', 'WIN 15 15'),
    (wythoff, '10 9\n', 'WIN 0 3'),
]


def main():
    bad = 0
    for idx, (mod, inp, want) in enumerate(CASES, 1):
        got = mod.solve(inp)
        ok = got == want
        if not ok:
            bad += 1
        print('case %d %s: got=%r want=%r' % (idx, 'OK' if ok else 'FAIL', got, want))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
