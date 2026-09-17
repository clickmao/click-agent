"""入口：``python3 -m sols <case_id>``。

从 stdin 读入该 case 的输入，把结果打印到 stdout。
"""
import sys

from sols.games import get_game


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        sys.stderr.write("usage: python3 -m sols <case_id>\n")
        return 2
    case_id = args[0]
    try:
        run = get_game(case_id)
    except KeyError:
        sys.stderr.write("unknown case_id: {}\n".format(case_id))
        return 2
    print(run(sys.stdin.read()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
