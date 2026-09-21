"""CLI 入口：python3 -m games <game_id>

从 stdin 读全部文本，调用对应模块的 solve(text)，
把返回值写到 stdout（末尾不带换行）。stderr 静默。
"""

import sys


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        return 2
    game_id = argv[0]

    if game_id == "life":
        from games import life as mod
    elif game_id == "sub":
        from games import sub as mod
    elif game_id == "nim":
        from games import nim as mod
    elif game_id == "wythoff":
        from games import wythoff as mod
    else:
        return 2

    text = sys.stdin.read()
    out = mod.solve(text)
    sys.stdout.write(out)
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
