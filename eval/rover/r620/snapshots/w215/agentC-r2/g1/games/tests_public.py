"""公开用例自验 (不通过网络, 只读内嵌期望值)。

运行: python3 games/tests_public.py
"""

from games import life, nim, sub, wythoff

LIFE_1 = """11 5 4
#....
.....
...#.
.#.#.
.....
.#..#
.#...
###.#
#.#.#
..#..
....#
"""
LIFE_1_EXP = """.....
.....
.....
.###.
.....
.....
..#..
.#.#.
...#.
..#..
....."""

LIFE_2 = """11 2 6
.#
##
..
##
.#
.#
..
#.
##
##
.#
"""
LIFE_2_EXP = """##
##
..
##
##
..
..
..
..
..
.."""

SUB_1 = "31 3\n1 6 10\n"
SUB_1_EXP = "WIN 6"
SUB_2 = "19 1\n1\n"
SUB_2_EXP = "WIN 1"

NIM_1 = "3\n5 9 4\n"
NIM_1_EXP = "WIN 2 8"
NIM_2 = "1\n3\n"
NIM_2_EXP = "WIN 1 3"

WY_1 = "21 25\n"
WY_1_EXP = "WIN 15 15"
WY_2 = "10 9\n"
WY_2_EXP = "WIN 0 3"


def check(name, got, exp):
    if got != exp:
        raise AssertionError("%s: got %r, expected %r" % (name, got, exp))


def main():
    check("life_1", life.solve(LIFE_1), LIFE_1_EXP)
    check("life_2", life.solve(LIFE_2), LIFE_2_EXP)
    check("sub_1", sub.solve(SUB_1), SUB_1_EXP)
    check("sub_2", sub.solve(SUB_2), SUB_2_EXP)
    check("nim_1", nim.solve(NIM_1), NIM_1_EXP)
    check("nim_2", nim.solve(NIM_2), NIM_2_EXP)
    check("wythoff_1", wythoff.solve(WY_1), WY_1_EXP)
    check("wythoff_2", wythoff.solve(WY_2), WY_2_EXP)
    print("ALL PUBLIC CASES OK")


if __name__ == "__main__":
    main()
