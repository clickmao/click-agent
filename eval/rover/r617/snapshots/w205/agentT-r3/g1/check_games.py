"""按各游戏 solve 直接调用公开用例，逐字节比对期望输出（自检脚本）。"""

from games import life, nim, sub, wythoff

CASES = [
    (life, '11 5 4\n#....\n.....\n...#.\n.#.#.\n.....\n.#..#\n.#...\n###.#\n#.#.#\n..#..\n....#', '.....\n.....\n.....\n.###.\n.....\n.....\n..#..\n.#.#.\n...#.\n..#..\n.....'),
    (life, '11 2 6\n.#\n##\n..\n##\n.#\n.#\n..\n#.\n##\n##\n.#', '##\n##\n..\n##\n##\n..\n..\n..\n..\n..\n..'),
    (sub, '31 3\n1 6 10', 'WIN 6'),
    (sub, '19 1\n1', 'WIN 1'),
    (nim, '3\n5 9 4', 'WIN 2 8'),
    (nim, '1\n3', 'WIN 1 3'),
    (wythoff, '21 25', 'WIN 15 15'),
    (wythoff, '10 9', 'WIN 0 3'),
]


def main() -> int:
    ok = True
    for mod, inp, exp in CASES:
        got = mod.solve(inp)
        if got != exp:
            ok = False
            print('FAIL %s' % mod.__name__)
            print('  got: %r' % got)
            print('  exp: %r' % exp)
    print('ALL_OK' if ok else 'SOME_FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
