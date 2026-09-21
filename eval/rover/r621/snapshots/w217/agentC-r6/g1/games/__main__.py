"""CLI 入口：python3 -m games <game_id>，从 stdin 读全部文本并输出 solve 的返回值。"""

import sys

from games import life, nim, sub, wythoff

_MODULES = {
    "life": life,
    "sub": sub,
    "nim": nim,
    "wythoff": wythoff,
}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    game_id = args[0]
    text = sys.stdin.read()
    out = _MODULES[game_id].solve(text)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
